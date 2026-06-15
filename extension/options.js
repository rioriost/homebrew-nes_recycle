(() => {
  "use strict";

  const N = globalThis.NesRecycleExtension;
  const ids = [
    "customerNumber",
    "lastName",
    "firstName",
    "postalCode",
    "address1",
    "address2",
    "phone",
    "email",
    "defaultCapsuleType",
    "defaultDate",
    "defaultTime",
    "defaultBags",
    "autoFill",
  ];

  function field(id) {
    return document.getElementById(id);
  }

  function setStatus(message, isError = false) {
    const status = field("status");
    status.textContent = message;
    status.classList.toggle("error", isError);
  }

  function readProfile() {
    return {
      customerNumber: field("customerNumber").value,
      lastName: field("lastName").value,
      firstName: field("firstName").value,
      postalCode: field("postalCode").value,
      address1: field("address1").value,
      address2: field("address2").value,
      phone: field("phone").value,
      email: field("email").value,
      defaultCapsuleType: field("defaultCapsuleType").value,
    };
  }

  function readSettings() {
    return {
      autoFill: field("autoFill").checked,
      defaultDate: field("defaultDate").value,
      defaultTime: field("defaultTime").value,
      defaultBags: field("defaultBags").value,
    };
  }

  function writeProfile(profile) {
    field("customerNumber").value = profile.customerNumber;
    field("lastName").value = profile.lastName;
    field("firstName").value = profile.firstName;
    field("postalCode").value = profile.postalCode;
    field("address1").value = profile.address1;
    field("address2").value = profile.address2;
    field("phone").value = profile.phone;
    field("email").value = profile.email;
    field("defaultCapsuleType").value = profile.defaultCapsuleType;
  }

  function writeSettings(settings) {
    field("defaultDate").value = settings.defaultDate;
    field("defaultTime").value = settings.defaultTime;
    field("defaultBags").value = settings.defaultBags;
    field("autoFill").checked = settings.autoFill;
  }

  async function load() {
    const state = await N.loadState();
    writeProfile(state.profile);
    writeSettings(state.settings);
  }

  async function save(event) {
    event.preventDefault();

    const validation = N.validateProfile(readProfile());
    if (!validation.ok) {
      setStatus(validation.errors.join("\n"), true);
      return;
    }

    await N.saveState(validation.profile, readSettings());
    writeProfile(validation.profile);
    writeSettings(N.sanitizeSettings(readSettings()));
    setStatus("保存しました。");
  }

  async function clear() {
    if (!globalThis.confirm("保存済みのプロフィールと既定値を削除しますか？")) {
      return;
    }

    await N.clearState();
    for (const id of ids) {
      const element = field(id);
      if (element.type === "checkbox") {
        element.checked = false;
      } else {
        element.value = "";
      }
    }
    field("defaultCapsuleType").value = "1";
    field("defaultTime").value = "";
    field("defaultBags").value = "1";
    setStatus("保存値を削除しました。");
  }

  document.getElementById("optionsForm").addEventListener("submit", save);
  document.getElementById("clearButton").addEventListener("click", clear);

  load().catch((error) => setStatus(error.message || String(error), true));
})();
