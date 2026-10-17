// ============================================================
// VOLTSAGE AI — AUTHENTICATION & SESSION HELPER
// Manages user profile state, navbar user pills, sidebar & route guard
// ============================================================

window.VoltSageAuth = {
    currentUser: null,

    async checkAuth() {
        const path = window.location.pathname;
        const isAuthPage = path.endsWith("login.html") || 
                           path.endsWith("register.html") ||
                           path === "/login" ||
                           path === "/register";

        try {
            const res = await fetch("/api/auth/me", {
                credentials: "include"
            });
            if (res.ok) {
                const data = await res.json();
                this.currentUser = data.user;
                this.updateNavbarUser(this.currentUser);
                this.updateSidebarUser(this.currentUser);

                // If already logged in and visiting login/register page, forward to maintenance workspace
                if (isAuthPage) {
                    window.location.href = "/maintenance.html";
                }
                return this.currentUser;
            } else {
                this.currentUser = null;
                if (!isAuthPage) {
                    window.location.href = "/login";
                    return null;
                }
                return null;
            }
        } catch (e) {
            console.warn("Auth check failed:", e);
            this.currentUser = null;
            if (!isAuthPage) {
                window.location.href = "/login";
            }
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
                    <span style="font-size: 10px; font-weight: 700; color: var(--accent-cyan); background: rgba(0, 210, 255, 0.15); padding: 1px 6px; border-radius: 3px;">
                        USER
                    </span>
                </div>
                <button type="button" class="btn btn-outline" style="padding: 5px 12px; font-size: 12px; border-radius: var(--radius-sm);" onclick="VoltSageAuth.logout()">
                    Sign Out
                </button>
            </div>
        `;
    },

    updateSidebarUser(user) {
        const sidebarFooter = document.getElementById("sidebar-user-footer");
        if (!sidebarFooter) return;

        sidebarFooter.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 10px; overflow: hidden;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--accent-gradient); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 800; flex-shrink: 0;">
                        ${(user.full_name || user.email).slice(0, 2).toUpperCase()}
                    </div>
                    <div style="overflow: hidden; line-height: 1.3;">
                        <div style="font-size: 12.5px; font-weight: 700; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            ${user.full_name || user.email}
                        </div>
                        <div style="font-size: 10.5px; color: var(--accent-cyan); font-weight: 700;">
                            Role: User
                        </div>
                    </div>
                </div>
                <button type="button" class="btn btn-outline" style="padding: 4px 8px; font-size: 11px; border-radius: var(--radius-sm);" title="Sign Out" onclick="VoltSageAuth.logout()">
                    Sign Out
                </button>
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
        window.location.href = "/login";
    }
};

document.addEventListener("DOMContentLoaded", function() {
    window.VoltSageAuth.checkAuth();
});
