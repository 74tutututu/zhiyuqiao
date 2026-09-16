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
        // Choosing a primary language also opts into that explanation language.
        // Never disable choices merely because their checkbox is not checked yet.
        const selected = languageInputs.find((input) => input.value === primaryLanguage.value);
        if (selected) selected.checked = true;
    }
    primaryLanguage?.addEventListener("change", syncPrimaryLanguage);
    languageInputs.forEach((input) => input.addEventListener("change", () => {
        if (!primaryLanguage) return;
        const checked = languageInputs.filter((item) => item.checked);
        if (checked.length && !checked.some((item) => item.value === primaryLanguage.value)) {
            primaryLanguage.value = checked[0].value;
        }
        syncPrimaryLanguage();
    }));
    form.addEventListener("submit", syncPrimaryLanguage);
    syncRolePanels();
    syncPrimaryLanguage();
})();
