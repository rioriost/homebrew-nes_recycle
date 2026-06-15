(() => {
  "use strict";

  const STORAGE_KEYS = {
    profile: "nesRecycleProfile",
    settings: "nesRecycleSettings",
  };

  const CAPSULE_TYPE_CODE_TO_LABEL = {
    1: "オリジナル",
    2: "ヴァーチュオ",
    3: "オリジナルとヴァーチュオ",
  };

  const DEFAULT_PROFILE = {
    customerNumber: "",
    lastName: "",
    firstName: "",
    postalCode: "",
    address1: "",
    address2: "",
    phone: "",
    email: "",
    defaultCapsuleType: "1",
  };

  const DEFAULT_SETTINGS = {
    autoFill: false,
    defaultDate: "",
    defaultTime: "",
    defaultBags: "1",
  };

  function extensionApi() {
    const api = globalThis.chrome || globalThis.browser;
    if (!api) {
      throw new Error("WebExtension API が見つかりません。");
    }
    return api;
  }

  function settleOnce(resolve, reject) {
    let settled = false;

    return {
      resolve(value) {
        if (!settled) {
          settled = true;
          resolve(value);
        }
      },
      reject(error) {
        if (!settled) {
          settled = true;
          reject(error instanceof Error ? error : new Error(String(error)));
        }
      },
    };
  }

  function storageGet(keys) {
    const api = extensionApi();

    return new Promise((resolve, reject) => {
      const settle = settleOnce(resolve, reject);
      const callback = (result) => {
        const lastError = api.runtime && api.runtime.lastError;
        if (lastError) {
          settle.reject(new Error(lastError.message));
          return;
        }
        settle.resolve(result || {});
      };

      try {
        const maybePromise = api.storage.local.get(keys, callback);
        if (maybePromise && typeof maybePromise.then === "function") {
          maybePromise.then((result) => settle.resolve(result || {}), settle.reject);
        }
      } catch (callbackError) {
        try {
          const maybePromise = api.storage.local.get(keys);
          if (maybePromise && typeof maybePromise.then === "function") {
            maybePromise.then((result) => settle.resolve(result || {}), settle.reject);
          } else {
            settle.resolve(maybePromise || {});
          }
        } catch (promiseError) {
          settle.reject(promiseError || callbackError);
        }
      }
    });
  }

  function storageSet(items) {
    const api = extensionApi();

    return new Promise((resolve, reject) => {
      const settle = settleOnce(resolve, reject);
      const callback = () => {
        const lastError = api.runtime && api.runtime.lastError;
        if (lastError) {
          settle.reject(new Error(lastError.message));
          return;
        }
        settle.resolve();
      };

      try {
        const maybePromise = api.storage.local.set(items, callback);
        if (maybePromise && typeof maybePromise.then === "function") {
          maybePromise.then(() => settle.resolve(), settle.reject);
        }
      } catch (callbackError) {
        try {
          const maybePromise = api.storage.local.set(items);
          if (maybePromise && typeof maybePromise.then === "function") {
            maybePromise.then(() => settle.resolve(), settle.reject);
          } else {
            settle.resolve();
          }
        } catch (promiseError) {
          settle.reject(promiseError || callbackError);
        }
      }
    });
  }

  function storageRemove(keys) {
    const api = extensionApi();

    return new Promise((resolve, reject) => {
      const settle = settleOnce(resolve, reject);
      const callback = () => {
        const lastError = api.runtime && api.runtime.lastError;
        if (lastError) {
          settle.reject(new Error(lastError.message));
          return;
        }
        settle.resolve();
      };

      try {
        const maybePromise = api.storage.local.remove(keys, callback);
        if (maybePromise && typeof maybePromise.then === "function") {
          maybePromise.then(() => settle.resolve(), settle.reject);
        }
      } catch (callbackError) {
        try {
          const maybePromise = api.storage.local.remove(keys);
          if (maybePromise && typeof maybePromise.then === "function") {
            maybePromise.then(() => settle.resolve(), settle.reject);
          } else {
            settle.resolve();
          }
        } catch (promiseError) {
          settle.reject(promiseError || callbackError);
        }
      }
    });
  }

  function digitsOnly(value) {
    return String(value || "").replace(/\D/g, "");
  }

  function normalizeCustomerNumber(value) {
    const digits = digitsOnly(value);
    return digits.length === 7 ? `0${digits}` : digits;
  }

  function normalizePostalCode(value) {
    return digitsOnly(value);
  }

  function normalizePhone(value) {
    return digitsOnly(value);
  }

  function normalizeCapsuleType(value) {
    const text = String(value || "").trim();
    if (CAPSULE_TYPE_CODE_TO_LABEL[text]) {
      return text;
    }

    const matched = Object.entries(CAPSULE_TYPE_CODE_TO_LABEL).find(([, label]) => label === text);
    return matched ? matched[0] : text;
  }

  function isValidCustomerNumber(value) {
    return /^\d{8}$/.test(normalizeCustomerNumber(value));
  }

  function isValidPostalCode(value) {
    return /^\d{7}$/.test(normalizePostalCode(value));
  }

  function isValidPhone(value) {
    const digits = normalizePhone(value);
    return digits.length >= 10 && digits.length <= 11;
  }

  function isValidEmail(value) {
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(value || "").trim());
  }

  function isValidCapsuleType(value) {
    return Object.prototype.hasOwnProperty.call(
      CAPSULE_TYPE_CODE_TO_LABEL,
      normalizeCapsuleType(value),
    );
  }

  function sanitizeProfile(profile) {
    const source = { ...DEFAULT_PROFILE, ...(profile || {}) };
    const defaultCapsuleType = normalizeCapsuleType(source.defaultCapsuleType || "1");

    return {
      customerNumber: normalizeCustomerNumber(source.customerNumber),
      lastName: String(source.lastName || "").trim(),
      firstName: String(source.firstName || "").trim(),
      postalCode: normalizePostalCode(source.postalCode),
      address1: String(source.address1 || "").trim(),
      address2: String(source.address2 || "").trim(),
      phone: normalizePhone(source.phone),
      email: String(source.email || "").trim(),
      defaultCapsuleType: isValidCapsuleType(defaultCapsuleType) ? defaultCapsuleType : "1",
    };
  }

  function validateProfile(profile) {
    const sanitized = sanitizeProfile(profile);
    const errors = [];

    if (!isValidCustomerNumber(sanitized.customerNumber)) {
      errors.push("お客様番号は7桁または8桁の数字で入力してください。");
    }
    if (!sanitized.lastName) {
      errors.push("姓を入力してください。");
    }
    if (!sanitized.firstName) {
      errors.push("名を入力してください。");
    }
    if (!isValidPostalCode(sanitized.postalCode)) {
      errors.push("郵便番号は7桁の数字で入力してください。");
    }
    if (!sanitized.address1) {
      errors.push("回収先住所を入力してください。");
    }
    if (!isValidPhone(sanitized.phone)) {
      errors.push("電話番号は10桁または11桁の数字で入力してください。");
    }
    if (!isValidEmail(sanitized.email)) {
      errors.push("メールアドレスの形式で入力してください。");
    }
    if (!isValidCapsuleType(sanitized.defaultCapsuleType)) {
      errors.push("カプセル種類は 1 / 2 / 3 のいずれかを選択してください。");
    }

    return {
      ok: errors.length === 0,
      errors,
      profile: sanitized,
    };
  }

  function splitPostalCode(postalCode) {
    const normalized = normalizePostalCode(postalCode);
    return [normalized.slice(0, 3), normalized.slice(3)];
  }

  function splitPhone(phone) {
    const digits = normalizePhone(phone);
    if (digits.length === 11) {
      return [digits.slice(0, 3), digits.slice(3, 7), digits.slice(7)];
    }
    if (digits.length === 10) {
      if (digits.startsWith("03") || digits.startsWith("06")) {
        return [digits.slice(0, 2), digits.slice(2, 6), digits.slice(6)];
      }
      return [digits.slice(0, 3), digits.slice(3, 6), digits.slice(6)];
    }
    throw new Error("電話番号の桁数が不正です。");
  }

  function toFullwidthAscii(text) {
    return String(text || "").replace(/[!-~ ]/g, (character) => {
      if (character === " ") {
        return "　";
      }
      return String.fromCharCode(character.charCodeAt(0) + 0xfee0);
    });
  }

  function normalizeIsoDate(value) {
    const text = String(value || "").trim();
    if (!text) {
      return "";
    }
    const match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) {
      return "";
    }

    const date = new Date(`${text}T00:00:00`);
    if (Number.isNaN(date.getTime())) {
      return "";
    }
    return text;
  }

  function sanitizeSettings(settings) {
    const source = { ...DEFAULT_SETTINGS, ...(settings || {}) };
    const defaultTime = ["", "AM", "14", "16", "18"].includes(source.defaultTime)
      ? source.defaultTime
      : "";
    const defaultBags = String(source.defaultBags || "1");

    return {
      autoFill: Boolean(source.autoFill),
      defaultDate: normalizeIsoDate(source.defaultDate),
      defaultTime,
      defaultBags: /^(10|[1-9])$/.test(defaultBags) ? defaultBags : "1",
    };
  }

  async function loadState() {
    const values = await storageGet([STORAGE_KEYS.profile, STORAGE_KEYS.settings]);
    return {
      profile: sanitizeProfile(values[STORAGE_KEYS.profile]),
      settings: sanitizeSettings(values[STORAGE_KEYS.settings]),
    };
  }

  async function saveState(profile, settings) {
    await storageSet({
      [STORAGE_KEYS.profile]: sanitizeProfile(profile),
      [STORAGE_KEYS.settings]: sanitizeSettings(settings),
    });
  }

  async function clearState() {
    await storageRemove([STORAGE_KEYS.profile, STORAGE_KEYS.settings]);
  }

  globalThis.NesRecycleExtension = {
    CAPSULE_TYPE_CODE_TO_LABEL,
    DEFAULT_PROFILE,
    DEFAULT_SETTINGS,
    extensionApi,
    loadState,
    saveState,
    clearState,
    normalizeCapsuleType,
    sanitizeProfile,
    sanitizeSettings,
    validateProfile,
    splitPostalCode,
    splitPhone,
    toFullwidthAscii,
    normalizeIsoDate,
  };
})();
