import './index.css';
import { createApp, reactive } from "vue";
import App from "./App.vue";

// Service Worker — offline rejimda URY Mosaic'ni qayta yuklashni qo'llab-quvvatlash
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {
      // SW ro'yxatdan o'tmasa, ilova muammosiz ishlashda davom etadi
    });
  });
}

import router from './router';

const app = createApp(App);

// Plugins
app.use(router);

// Global Properties,
// components can inject this

// Configure route gaurds
router.beforeEach(async (to, from, next) => {
	if (to.matched.some((record) => !record.meta.isLoginPage)) {
		// this route requires auth, check if logged in
		// if not, redirect to login page.
		if (!auth.isLoggedIn) {
			next({ name: 'Login', query: { route: to.path } });
		} else {
			next();
		}
	} else {
		if (auth.isLoggedIn) {
			next({ name: 'Home' });
		} else {
			next();
		}
	}
});

app.mount("#app");
