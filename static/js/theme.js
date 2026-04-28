document.addEventListener("DOMContentLoaded", () => {
    const root = document.documentElement;

    const bgColorPicker = document.getElementById("bgColor");
    const navColorPicker = document.getElementById("navColor");
    const btnColorPicker = document.getElementById("btnColor");
    const resetBtn = document.getElementById("resetTheme");

    const defaultTheme = {
        bg: "#f0fcf4",
        nav: "#ffffff",
        btn: "#27ae60"
    };

    // Load saved theme
    const savedBg = localStorage.getItem("theme_bg");
    const savedNav = localStorage.getItem("theme_nav");
    const savedBtn = localStorage.getItem("theme_btn");

    if (savedBg) {
        root.style.setProperty("--bg-color", savedBg);
        if(bgColorPicker) bgColorPicker.value = savedBg;
    }
    if (savedNav) {
        root.style.setProperty("--nav-color", savedNav);
        if(navColorPicker) navColorPicker.value = savedNav;
    }
    if (savedBtn) {
        root.style.setProperty("--btn-color", savedBtn);
        if(btnColorPicker) btnColorPicker.value = savedBtn;
    }

    // Attach listeners
    if (bgColorPicker) {
        bgColorPicker.addEventListener("input", (e) => {
            const color = e.target.value;
            root.style.setProperty("--bg-color", color);
            localStorage.setItem("theme_bg", color);
        });
    }

    if (navColorPicker) {
        navColorPicker.addEventListener("input", (e) => {
            const color = e.target.value;
            root.style.setProperty("--nav-color", color);
            localStorage.setItem("theme_nav", color);
        });
    }

    if (btnColorPicker) {
        btnColorPicker.addEventListener("input", (e) => {
            const color = e.target.value;
            root.style.setProperty("--btn-color", color);
            localStorage.setItem("theme_btn", color);
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            root.style.setProperty("--bg-color", defaultTheme.bg);
            root.style.setProperty("--nav-color", defaultTheme.nav);
            root.style.setProperty("--btn-color", defaultTheme.btn);
            
            if(bgColorPicker) bgColorPicker.value = defaultTheme.bg;
            if(navColorPicker) navColorPicker.value = defaultTheme.nav;
            if(btnColorPicker) btnColorPicker.value = defaultTheme.btn;

            localStorage.removeItem("theme_bg");
            localStorage.removeItem("theme_nav");
            localStorage.removeItem("theme_btn");
        });
    }
});
