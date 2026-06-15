(() => {
  "use strict";

  const N = globalThis.NesRecycleExtension;

  function field(id) {
    return document.getElementById(id);
  }

  function setStatus(message, isError = false) {
    const status = field("status");
    status.textContent = message;
    status.classList.toggle("error", isError);
  }

  function apiCall(invoker) {
    const api = N.extensionApi();

    return new Promise((resolve, reject) => {
      let settled = false;
      const done = (value) => {
        if (!settled) {
          settled = true;
          resolve(value);
        }
      };
      const fail = (error) => {
        if (!settled) {
          settled = true;
          reject(error instanceof Error ? error : new Error(String(error)));
        }
      };
      const callback = (result) => {
        const lastError = api.runtime && api.runtime.lastError;
        if (lastError) {
          fail(new Error(lastError.message));
          return;
        }
        done(result);
      };

      try {
        const maybePromise = invoker(callback);
        if (maybePromise && typeof maybePromise.then === "function") {
          maybePromise.then(done, fail);
        }
      } catch (error) {
        fail(error);
      }
    });
  }

  async function activeTab() {
    const api = N.extensionApi();
    const tabs = await apiCall((callback) =>
      api.tabs.query(
        {
          active: true,
          currentWindow: true,
        },
        callback,
      ),
    );
    return tabs && tabs[0];
  }

  async function sendFillMessage(tabId, overrides) {
    const api = N.extensionApi();
    return apiCall((callback) =>
      api.tabs.sendMessage(
        tabId,
        {
          target: "nes-recycle",
          type: "fill",
          overrides,
        },
        callback,
      ),
    );
  }

  function readOverrides() {
    return {
      dateIso: field("dateIso").value,
      timeValue: field("timeValue").value,
      capsuleType: field("capsuleType").value,
      bags: field("bags").value,
    };
  }

  async function load() {
    const state = await N.loadState();
    const validation = N.validateProfile(state.profile);

    field("dateIso").value = state.settings.defaultDate;
    field("timeValue").value = state.settings.defaultTime;
    field("capsuleType").value = state.profile.defaultCapsuleType;
    field("bags").value = state.settings.defaultBags;

    if (!validation.ok) {
      field("fillButton").disabled = true;
      setStatus("先に設定画面でプロフィールを保存してください。", true);
      return;
    }

    setStatus("回収フォームの入力画面で実行してください。");
  }

  async function fill() {
    const tab = await activeTab();
    if (!tab || !tab.id) {
      setStatus("現在のタブを取得できませんでした。", true);
      return;
    }

    try {
      const result = await sendFillMessage(tab.id, readOverrides());
      if (result && result.ok) {
        setStatus("入力しました。確認画面へ進む前に内容を確認してください。");
        return;
      }

      const messages = [
        ...((result && result.errors) || []),
        ...((result && result.warnings) || []),
      ];
      setStatus(messages.join("\n") || "入力できませんでした。", true);
    } catch (error) {
      setStatus(
        "このタブでは実行できません。回収フォームの入力画面を開いてから再実行してください。",
        true,
      );
    }
  }

  function openOptions() {
    const api = N.extensionApi();
    if (api.runtime.openOptionsPage) {
      api.runtime.openOptionsPage();
    }
  }

  document.getElementById("fillButton").addEventListener("click", fill);
  document.getElementById("optionsButton").addEventListener("click", openOptions);

  load().catch((error) => setStatus(error.message || String(error), true));
})();
