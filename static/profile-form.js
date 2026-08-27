(function () {
    const form = document.querySelector("[data-profile-form]");
    if (!form) return;

    const roleInputs = Array.from(form.querySelectorAll('input[name="account_role"]'));
    const panels = Array.from(form.querySelectorAll("[data-role-panel]"));
    const languageInputs = Array.from(form.querySelectorAll('input[name="teaching_languages"]'));
    const primaryLanguage = form.querySelector('select[name="primary_language"]');

    function syncRolePanels() {
        const role = roleInputs.find((input) => input.checked)?.value || "student";
        panels.forEach((panel) => {
            const active = panel.dataset.rolePanel === role;
            panel.hidden = !active;
            panel.querySelectorAll("input, select, textarea").forEach((field) => {
                field.disabled = !active;
            });
        });
    }

    roleInputs.forEach((input) => input.addEventListener("change", syncRolePanels));
    function syncPrimaryLanguage() {
        if (!primaryLanguage) return;
        const enabled = languageInputs.filter((input) => input.checked).map((input) => input.value);
        Array.from(primaryLanguage.options).forEach((option) => {
            option.disabled = !enabled.includes(option.value);
        });
        if (!enabled.includes(primaryLanguage.value) && enabled.length) primaryLanguage.value = enabled[0];
    }
    languageInputs.forEach((input) => input.addEventListener("change", syncPrimaryLanguage));
    syncRolePanels();
    syncPrimaryLanguage();
})();
