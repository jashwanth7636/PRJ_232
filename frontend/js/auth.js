// ============================================================
// VOLTSAGE AI — AUTHENTICATION & SESSION HELPER
// Manages user profile state, navbar user pills & logout
// ============================================================

window.VoltSageAuth = {
    currentUser: null,

    async checkAuth() {
        try {
            const res = await fetch("/api/auth/me", {
                credentials: "include"
            });
            if (res.ok) {
                const data = await res.json();
                this.currentUser = data.user;
                this.updateNavbarUser(this.currentUser);
                return this.currentUser;
            } else {
                this.currentUser = null;
                this.updateNavbarGuest();
                return null;
            }
        } catch (e) {
            console.warn("Auth check failed:", e);
            this.currentUser = null;
            this.updateNavbarGuest();
            return null;
        }
    },

    updateNavbarUser(user) {
        const container = document.getElementById("navbar-auth-section");
        if (!container) return;

        container.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 8px; padding: 4px 10px; background: rgba(0, 210, 255, 0.08); border: 1px solid rgba(0, 210, 255, 0.2); border-radius: var(--radius-pill); font-size: 12px;">
                    <span style="width: 22px; height: 22px; border-radius: 50%; background: var(--accent-gradient); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 800;">
                        ${(user.full_name || user.email).slice(0, 2).toUpperCase()}
                    </span>
                    <span style="color: #fff; font-weight: 600; max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        ${user.full_name || user.email}
                    </span>
                </div>
                <button type="button" class="btn btn-outline" style="padding: 5px 12px; font-size: 12px; border-radius: var(--radius-sm);" onclick="VoltSageAuth.logout()">
                    Sign Out
                </button>
            </div>
        `;
    },

    updateNavbarGuest() {
        const container = document.getElementById("navbar-auth-section");
        if (!container) return;

        container.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <a href="login.html" class="btn btn-outline" style="padding: 5px 12px; font-size: 12px; border-radius: var(--radius-sm);">
                    Sign In
                </a>
                <a href="register.html" class="btn btn-primary" style="padding: 5px 12px; font-size: 12px; border-radius: var(--radius-sm);">
                    Register
                </a>
            </div>
        `;
    },

    async logout() {
        try {
            await fetch("/api/auth/logout", {
                method: "POST",
                credentials: "include"
            });
        } catch (e) {
            console.error("Logout error:", e);
        }
        localStorage.removeItem("voltsage_active_conv");
        window.location.href = "login.html";
    }
};

document.addEventListener("DOMContentLoaded", function() {
    window.VoltSageAuth.checkAuth();
});
