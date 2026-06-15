(() => {
  "use strict";

  const N = globalThis.NesRecycleExtension;
  const FORM_NAME = "newdoc";

  function entryForm() {
    return document.forms.namedItem(FORM_NAME) || document.getElementById(FORM_NAME);
  }

  function isEntryFormPage() {
    const form = entryForm();
    if (!form) {
      return false;
    }

    const customerNumber = namedElements("survey1")[0];
    return Boolean(customerNumber && customerNumber.type !== "hidden");
  }

  function namedElements(name) {
    const form = entryForm();
    const elements = [];

    if (form && form.elements && form.elements[name]) {
      const item = form.elements[name];
      if (item.tagName) {
        elements.push(item);
      } else if (typeof item.length === "number") {
        elements.push(...Array.from(item));
      }
    }

    if (elements.length === 0) {
      elements.push(...Array.from(document.getElementsByName(name)));
    }

    return elements;
  }

  function dispatchFieldEvents(element) {
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function setText(name, value, warnings) {
    const element = namedElements(name)[0];
    if (!element) {
      warnings.push(`${name} が見つかりません。`);
      return;
    }
    element.value = value;
    dispatchFieldEvents(element);
  }

  function setSelect(name, value, warnings) {
    const element = namedElements(name)[0];
    if (!element) {
      warnings.push(`${name} が見つかりません。`);
      return;
    }

    const option = Array.from(element.options || []).find(
      (candidate) => candidate.value === value || candidate.textContent.trim() === value,
    );
    if (!option) {
      warnings.push(`${name} に ${value} の選択肢が見つかりません。`);
      return;
    }

    element.value = option.value;
    dispatchFieldEvents(element);
  }

  function setCheckbox(name, checked, warnings) {
    const element = namedElements(name)[0];
    if (!element) {
      warnings.push(`${name} が見つかりません。`);
      return;
    }
    element.checked = checked;
    dispatchFieldEvents(element);
  }

  function setRadio(name, value, warnings) {
    const elements = namedElements(name);
    const radio = elements.find((element) => element.value === value);
    if (!radio) {
      warnings.push(`${name} に ${value || "指定なし"} の選択肢が見つかりません。`);
      return;
    }
    radio.checked = true;
    dispatchFieldEvents(radio);
  }

  function setAttributes(name, attributes) {
    for (const element of namedElements(name)) {
      for (const [attribute, value] of Object.entries(attributes)) {
        element.setAttribute(attribute, value);
      }
      element.dataset.nesRecycleEnhanced = "true";
    }
  }

  function enhanceAutocomplete() {
    if (!isEntryFormPage()) {
      return;
    }

    setAttributes("survey1", {
      autocomplete: "off",
      inputmode: "numeric",
    });
    setAttributes("name1", { autocomplete: "family-name" });
    setAttributes("name2", { autocomplete: "given-name" });
    setAttributes("zip1", {
      autocomplete: "postal-code",
      inputmode: "numeric",
    });
    setAttributes("zip2", {
      autocomplete: "postal-code",
      inputmode: "numeric",
    });
    setAttributes("address1", { autocomplete: "address-line1" });
    setAttributes("address2", { autocomplete: "address-line2" });
    setAttributes("tel1_1", {
      autocomplete: "tel-national",
      inputmode: "numeric",
    });
    setAttributes("tel1_2", {
      autocomplete: "tel-national",
      inputmode: "numeric",
    });
    setAttributes("tel1_3", {
      autocomplete: "tel-national",
      inputmode: "numeric",
    });
    setAttributes("email", { autocomplete: "email" });
    setAttributes("email_check", { autocomplete: "email" });
  }

  function siteMinimumDate() {
    const text = document.body ? document.body.innerText : "";
    const match = text.match(/(\d{4})\/(\d{1,2})\/(\d{1,2})以降/);
    if (!match) {
      return "";
    }

    const [, year, month, day] = match;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }

  function resolveFillValues(state, overrides) {
    const validation = N.validateProfile(state.profile);
    if (!validation.ok) {
      return {
        ok: false,
        errors: validation.errors,
      };
    }

    const profile = validation.profile;
    const settings = N.sanitizeSettings(state.settings);
    const [zip1, zip2] = N.splitPostalCode(profile.postalCode);
    const [tel1, tel2, tel3] = N.splitPhone(profile.phone);
    const hasOverride = (key) => Object.prototype.hasOwnProperty.call(overrides, key);
    const capsuleType = N.normalizeCapsuleType(
      hasOverride("capsuleType") ? overrides.capsuleType : profile.defaultCapsuleType || "1",
    );
    const capsuleLabel = N.CAPSULE_TYPE_CODE_TO_LABEL[capsuleType];
    const dateIso =
      N.normalizeIsoDate(hasOverride("dateIso") ? overrides.dateIso : settings.defaultDate) ||
      siteMinimumDate();
    const requestedTime = hasOverride("timeValue") ? overrides.timeValue : settings.defaultTime;
    const timeValue = ["", "AM", "14", "16", "18"].includes(requestedTime)
      ? requestedTime
      : "";
    const requestedBags = hasOverride("bags") ? overrides.bags : settings.defaultBags;
    const bags = /^(10|[1-9])$/.test(String(requestedBags || ""))
      ? String(requestedBags)
      : "1";

    return {
      ok: true,
      values: {
        survey1: profile.customerNumber,
        name1: N.toFullwidthAscii(profile.lastName),
        name2: N.toFullwidthAscii(profile.firstName),
        zip1,
        zip2,
        address1: N.toFullwidthAscii(profile.address1),
        address2: N.toFullwidthAscii(profile.address2),
        tel1_1: tel1,
        tel1_2: tel2,
        tel1_3: tel3,
        email: profile.email,
        email_check: profile.email,
        receipt_day_button: "1",
        receipt_time: timeValue,
        survey3: true,
        free_select_answer3: true,
        free_select_answer2: true,
        free_select_answer1: capsuleLabel,
        daisu: bags,
        dateIso,
      },
    };
  }

  async function fillForm(overrides = {}) {
    if (!isEntryFormPage()) {
      return {
        ok: false,
        errors: ["対象フォームが見つかりません。回収フォームの入力画面で実行してください。"],
      };
    }

    enhanceAutocomplete();

    const state = await N.loadState();
    const resolved = resolveFillValues(state, overrides);
    if (!resolved.ok) {
      return resolved;
    }

    const warnings = [];
    const { values } = resolved;

    setText("survey1", values.survey1, warnings);
    setText("name1", values.name1, warnings);
    setText("name2", values.name2, warnings);
    setText("zip1", values.zip1, warnings);
    setText("zip2", values.zip2, warnings);
    setText("address1", values.address1, warnings);
    setText("address2", values.address2, warnings);
    setText("tel1_1", values.tel1_1, warnings);
    setText("tel1_2", values.tel1_2, warnings);
    setText("tel1_3", values.tel1_3, warnings);
    setText("email", values.email, warnings);
    setText("email_check", values.email_check, warnings);

    setRadio("receipt_day_button", values.receipt_day_button, warnings);
    if (values.dateIso) {
      const [year, month, day] = values.dateIso.split("-");
      setText("receipt_day1", year, warnings);
      setText("receipt_day2", month, warnings);
      setText("receipt_day3", day, warnings);
    } else {
      warnings.push("回収希望日は空欄のままです。フォーム上の指定可能日を確認してください。");
    }
    setRadio("receipt_time", values.receipt_time, warnings);

    setCheckbox("survey3", values.survey3, warnings);
    setCheckbox("free_select_answer3", values.free_select_answer3, warnings);
    setCheckbox("free_select_answer2", values.free_select_answer2, warnings);
    setSelect("free_select_answer1", values.free_select_answer1, warnings);
    setSelect("daisu", values.daisu, warnings);

    return {
      ok: warnings.length === 0,
      warnings,
    };
  }

  async function boot() {
    enhanceAutocomplete();

    const state = await N.loadState();
    if (state.settings.autoFill) {
      await fillForm();
    }
  }

  const api = N.extensionApi();
  api.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message || message.target !== "nes-recycle") {
      return false;
    }

    if (message.type === "fill") {
      fillForm(message.overrides || {})
        .then((result) => sendResponse(result))
        .catch((error) =>
          sendResponse({
            ok: false,
            errors: [error.message || String(error)],
          }),
        );
      return true;
    }

    if (message.type === "enhance") {
      enhanceAutocomplete();
      sendResponse({ ok: true });
      return false;
    }

    return false;
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
