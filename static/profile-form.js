(function () {
    const form = document.querySelector("[data-profile-form]");
    if (!form) return;

    const roleInputs = Array.from(form.querySelectorAll('input[name="account_role"]'));
    const panels = Array.from(form.querySelectorAll("[data-role-panel]"));

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
    syncRolePanels();
})();
