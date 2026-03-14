<template>
  <div style="height: calc(100vh - 64px); display: flex; flex-direction: column; padding: 12px; gap: 12px; box-sizing: border-box;">

    <!-- Auth Modal -->
    <div v-if="showModal" class="fixed inset-0 z-50 bg-black bg-opacity-40 flex items-center justify-center">
      <div class="bg-white rounded-xl p-8 shadow-2xl w-full max-w-sm">
        <p class="text-lg font-semibold text-gray-800 mb-2">
          <span class="inline-block w-3 h-3 rounded-full bg-red-500 mr-2"></span>Not Permitted
        </p>
        <hr class="mb-4" />
        <p class="text-gray-500 mb-6">Log in to access this page.</p>
        <button @click="showModal = false; redirectToLogin();"
          class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition">
          Login
        </button>
      </div>
    </div>

    <!-- 3-Column Layout -->
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; flex: 1; overflow: hidden; min-height: 0;">

      <!-- ===== YANGI BUYURTMALAR ===== -->
      <div style="display: flex; flex-direction: column; overflow: hidden; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.12);">
        <div style="background: #2563EB; color: white; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border-radius: 12px 12px 0 0; flex-shrink: 0;">
          <span style="font-weight: 700; font-size: 13px; letter-spacing: 1.5px;">YANGI BUYURTMALAR</span>
          <span style="background: #1D4ED8; color: white; font-size: 13px; font-weight: 700; padding: 2px 10px; border-radius: 999px;">{{ visibleCount(yangi) }}</span>
        </div>
        <div style="flex: 1; overflow-y: auto; padding: 10px; background: #EFF6FF; display: flex; flex-direction: column; gap: 10px;">
          <template v-for="kot in yangi" :key="kot.name">
            <div
              v-show="!kot.showDiv && kot.production === production"
              :style="cardStyle(kot)"
              style="border-radius: 12px; padding: 12px; position: relative; box-shadow: 0 1px 4px rgba(0,0,0,0.08); cursor: pointer;"
              @click="rotateCard(kot)"
            >
              <!-- Action overlay -->
              <div v-if="kot.isRotated"
                style="position: absolute; inset: 0; background: rgba(255,255,255,0.92); z-index: 10; border-radius: 12px; display: flex; justify-content: center; align-items: center;">
                <button
                  @click.stop="isCancelled(kot) ? confirmOrder(kot) : startPreparation(kot)"
                  style="background: #2563EB; color: white; padding: 10px 32px; border-radius: 8px; font-size: 15px; font-weight: 600; border: none; cursor: pointer;">
                  {{ isCancelled(kot) ? 'Tasdiqlash' : 'Tayyorlash' }}
                </button>
              </div>
              <!-- Header -->
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <div style="font-size: 13px; line-height: 1.6;">
                  <div>
                    <span style="color: #6B7280;" v-if="kot.tableortakeaway !== 'Takeaway'">Table </span>
                    <span style="font-weight: 700; color: #111;">{{ kot.tableortakeaway }}</span>
                    <span style="color: #6B7280; font-size: 12px;"> ({{ kot.user }})</span>
                  </div>
                  <div v-if="kot.is_aggregator">
                    <span style="color: #6B7280;">Aggregator: </span>
                    <span style="font-weight: 600;">{{ kot.customer_name }}</span>
                  </div>
                  <div v-if="kot.is_aggregator">
                    <span style="color: #6B7280;">ID: </span>
                    <span style="font-weight: 600;">{{ kot.aggregator_id }}</span>
                  </div>
                  <div>
                    <span style="color: #6B7280;">Order </span>
                    <span style="font-weight: 700;">#{{ daily_order_number ? kot.order_no : kot.invoice.slice(-4) }}</span>
                    <span v-if="isCancelled(kot)" style="color: #DC2626; font-size: 12px; margin-left: 4px;">({{ kot.type }})</span>
                  </div>
                </div>
                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 2px;">
                  <span v-if="kot.ticket_number"
                    style="background: #111; color: #fff; font-size: 18px; font-weight: 900; padding: 1px 10px; border-radius: 6px; letter-spacing: 1px;">
                    {{ kot.ticket_number }}
                  </span>
                  <span :style="{ color: kot.timecolor || '#111' }" style="font-weight: 700; font-size: 20px; white-space: nowrap;">
                    {{ kot.timeRemaining }}
                  </span>
                </div>
              </div>
              <div v-if="kot.type === 'Duplicate'" style="color: #DC2626; font-size: 12px; font-weight: 600; margin-bottom: 6px;">
                ⚠ Duplicate KOT — CHECK WITH CAPTAIN
              </div>
              <div v-if="kot.comments" style="color: #6B7280; font-size: 12px; margin-bottom: 6px;">({{ kot.comments }})</div>
              <!-- Items -->
              <div v-for="kotitem in sortedKotItems(kot)" :key="kotitem.name">
                <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 14px; padding: 3px 0;">
                  <span>
                    {{ kotitem.item_name }}
                    <span v-if="kotitem.indicate_course" style="color: #9CA3AF; font-size: 12px; font-weight: 400;"> ({{ kotitem.course }})</span>
                    <span v-if="isCancelled(kot)" style="color: #DC2626; font-size: 12px; font-weight: 400;"> [Old: {{ kotitem.quantity }}]</span>
                  </span>
                  <span style="margin-left: 8px; flex-shrink: 0;">{{ kotitem.qty }}</span>
                </div>
                <p v-if="kotitem.comments" style="color: #6B7280; font-size: 12px; margin: 0 0 2px 0;">{{ kotitem.comments }}</p>
                <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 4px 0;" />
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- ===== TAYYORLANMOQDA ===== -->
      <div style="display: flex; flex-direction: column; overflow: hidden; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.12);">
        <div style="background: #F97316; color: white; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border-radius: 12px 12px 0 0; flex-shrink: 0;">
          <span style="font-weight: 700; font-size: 13px; letter-spacing: 1.5px;">TAYYORLANMOQDA</span>
          <span style="background: #EA6C10; color: white; font-size: 13px; font-weight: 700; padding: 2px 10px; border-radius: 999px;">{{ visibleCount(tayyorlanmoqda) }}</span>
        </div>
        <div style="flex: 1; overflow-y: auto; padding: 10px; background: #FFF7ED; display: flex; flex-direction: column; gap: 10px;">
          <template v-for="kot in tayyorlanmoqda" :key="kot.name">
            <div
              v-show="!kot.showDiv && kot.production === production"
              :style="cardStyle(kot)"
              style="border-radius: 12px; padding: 12px; position: relative; box-shadow: 0 1px 4px rgba(0,0,0,0.08); cursor: pointer;"
              @click="rotateCard(kot)"
            >
              <div v-if="kot.isRotated"
                style="position: absolute; inset: 0; background: rgba(255,255,255,0.92); z-index: 10; border-radius: 12px; display: flex; justify-content: center; align-items: center;">
                <button @click.stop="markReady(kot)"
                  style="background: #F97316; color: white; padding: 10px 32px; border-radius: 8px; font-size: 15px; font-weight: 600; border: none; cursor: pointer;">
                  Tayyor
                </button>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <div style="font-size: 13px; line-height: 1.6;">
                  <div>
                    <span style="color: #6B7280;" v-if="kot.tableortakeaway !== 'Takeaway'">Table </span>
                    <span style="font-weight: 700; color: #111;">{{ kot.tableortakeaway }}</span>
                    <span style="color: #6B7280; font-size: 12px;"> ({{ kot.user }})</span>
                  </div>
                  <div>
                    <span style="color: #6B7280;">Order </span>
                    <span style="font-weight: 700;">#{{ daily_order_number ? kot.order_no : kot.invoice.slice(-4) }}</span>
                  </div>
                </div>
                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 2px;">
                  <span v-if="kot.ticket_number"
                    style="background: #111; color: #fff; font-size: 18px; font-weight: 900; padding: 1px 10px; border-radius: 6px; letter-spacing: 1px;">
                    {{ kot.ticket_number }}
                  </span>
                  <span :style="{ color: kot.timecolor || '#111' }" style="font-weight: 700; font-size: 20px; white-space: nowrap;">
                    {{ kot.timeRemaining }}
                  </span>
                </div>
              </div>
              <div v-if="kot.comments" style="color: #6B7280; font-size: 12px; margin-bottom: 6px;">({{ kot.comments }})</div>
              <div v-for="kotitem in sortedKotItems(kot)" :key="kotitem.name">
                <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 14px; padding: 3px 0;">
                  <span>
                    {{ kotitem.item_name }}
                    <span v-if="kotitem.indicate_course" style="color: #9CA3AF; font-size: 12px; font-weight: 400;"> ({{ kotitem.course }})</span>
                  </span>
                  <span style="margin-left: 8px; flex-shrink: 0;">{{ kotitem.qty }}</span>
                </div>
                <p v-if="kotitem.comments" style="color: #6B7280; font-size: 12px; margin: 0 0 2px 0;">{{ kotitem.comments }}</p>
                <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 4px 0;" />
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- ===== TAYYOR ===== -->
      <div style="display: flex; flex-direction: column; overflow: hidden; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.12);">
        <div style="background: #16A34A; color: white; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border-radius: 12px 12px 0 0; flex-shrink: 0;">
          <span style="font-weight: 700; font-size: 13px; letter-spacing: 1.5px;">TAYYOR</span>
          <span style="background: #15803D; color: white; font-size: 13px; font-weight: 700; padding: 2px 10px; border-radius: 999px;">{{ visibleCount(tayyor) }}</span>
        </div>
        <div style="flex: 1; overflow-y: auto; padding: 10px; background: #F0FDF4; display: flex; flex-direction: column; gap: 10px;">
          <template v-for="kot in tayyor" :key="kot.name">
            <div
              v-show="!kot.showDiv && kot.production === production"
              :style="cardStyle(kot)"
              style="border-radius: 12px; padding: 12px; position: relative; box-shadow: 0 1px 4px rgba(0,0,0,0.08); cursor: pointer;"
              @click="rotateCard(kot)"
            >
              <div v-if="kot.isRotated"
                style="position: absolute; inset: 0; background: rgba(255,255,255,0.92); z-index: 10; border-radius: 12px; display: flex; justify-content: center; align-items: center;">
                <button @click.stop="serveOrder(kot)"
                  style="background: #16A34A; color: white; padding: 10px 32px; border-radius: 8px; font-size: 15px; font-weight: 600; border: none; cursor: pointer;">
                  Yetkazib berildi
                </button>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <div style="font-size: 13px; line-height: 1.6;">
                  <div>
                    <span style="color: #6B7280;" v-if="kot.tableortakeaway !== 'Takeaway'">Table </span>
                    <span style="font-weight: 700; color: #111;">{{ kot.tableortakeaway }}</span>
                    <span style="color: #6B7280; font-size: 12px;"> ({{ kot.user }})</span>
                  </div>
                  <div>
                    <span style="color: #6B7280;">Order </span>
                    <span style="font-weight: 700;">#{{ daily_order_number ? kot.order_no : kot.invoice.slice(-4) }}</span>
                  </div>
                </div>
                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 2px;">
                  <span v-if="kot.ticket_number"
                    style="background: #111; color: #fff; font-size: 18px; font-weight: 900; padding: 1px 10px; border-radius: 6px; letter-spacing: 1px;">
                    {{ kot.ticket_number }}
                  </span>
                  <span :style="{ color: kot.timecolor || '#111' }" style="font-weight: 700; font-size: 20px; white-space: nowrap;">
                    {{ kot.timeRemaining }}
                  </span>
                </div>
              </div>
              <div v-if="kot.comments" style="color: #6B7280; font-size: 12px; margin-bottom: 6px;">({{ kot.comments }})</div>
              <div v-for="kotitem in sortedKotItems(kot)" :key="kotitem.name">
                <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 14px; padding: 3px 0;">
                  <span>
                    {{ kotitem.item_name }}
                    <span v-if="kotitem.indicate_course" style="color: #9CA3AF; font-size: 12px; font-weight: 400;"> ({{ kotitem.course }})</span>
                  </span>
                  <span style="margin-left: 8px; flex-shrink: 0;">{{ kotitem.qty }}</span>
                </div>
                <p v-if="kotitem.comments" style="color: #6B7280; font-size: 12px; margin: 0 0 2px 0;">{{ kotitem.comments }}</p>
                <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 4px 0;" />
              </div>
            </div>
          </template>
        </div>
      </div>

    </div>

    <!-- Audio Alert -->
    <div v-if="showAudioAlertMessage"
      style="position: absolute; top: 8px; left: 50%; transform: translateX(-50%); font-size: 20px; font-weight: 700; color: #DC2626; text-align: center;">
      Audio notifications disabled. Click anywhere to enable.
    </div>

    <!-- Online/Offline toast -->
    <div v-if="statusMessage"
      :style="{ background: isOnline ? '#16A34A' : '#DC2626' }"
      style="position: fixed; bottom: 24px; right: 24px; color: white; padding: 12px 20px; border-radius: 10px; font-weight: 600; z-index: 100;">
      {{ statusMessage }}
    </div>

  </div>
</template>

<script>
import { FrappeApp } from "frappe-js-sdk";
import io from "socket.io-client";

let host = window.location.hostname;
let protocol = window.location.protocol;
// API calls go to the web server (same origin)
let apiUrl = `${protocol}//${host}${window.location.port ? ':' + window.location.port : ''}`;
// Socket.io connects to the socketio server (port 9000 in dev, same origin in prod)
let socketUrl = window.location.port
  ? `${protocol}//${host}:${window.socketio_port || 9000}`
  : `${protocol}//${host}`;
window.globalSiteName = '';
let socket;

async function fetchAndSetSiteName() {
  try {
    const res = await fetch('/api/method/ury.ury.api.ury_kot_display.get_site_name', {
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    window.globalSiteName = data.message.site_name;
  } catch (e) {
    console.error('Failed to fetch site name:', e);
  }
}

async function initializeSocket() {
  await fetchAndSetSiteName();
  if (window.globalSiteName) {
    socket = io(`${socketUrl}/${window.globalSiteName}`, { withCredentials: true });
    socket.on('connect_error', (e) => console.error("Socket error:", e));
    socket.on('connect', () => console.log('Socket connected'));
  }
  return socket;
}

const frappe = new FrappeApp(apiUrl);

export default {
  data() {
    return {
      yangi: [],
      tayyorlanmoqda: [],
      tayyor: [],
      call: frappe.call(),
      production: "",
      branch: "",
      kot_channel: "",
      loggeduser: "",
      showModal: false,
      kot_alert_time: "",
      showAudioAlertMessage: false,
      audio_alert: 0,
      isOnline: navigator.onLine,
      statusMessage: "",
      daily_order_number: 0,
      _pollInterval: null,
    };
  },

  computed: {
    sortedKotItems() {
      return (kot) => [...(kot.kot_items || [])].sort((a, b) => a.serve_priority - b.serve_priority);
    },
  },

  methods: {
    isCancelled(kot) {
      return kot.type === 'Cancelled' || kot.type === 'Partially cancelled';
    },

    visibleCount(list) {
      return list.filter(k => !k.showDiv && k.production === this.production).length;
    },

    cardStyle(kot) {
      if (kot.type === "Order Modified") return "background: #FFD493; border: 1px solid #FFC700;";
      if (this.isCancelled(kot))          return "background: #FFD2D2; border: 1px solid #FAA7A7;";
      if (!kot.restaurant_table || kot.table_takeaway == 1) return "background: #DBEAFE; border: 1px solid #BFDBFE;";
      return "background: #FFFFFF; border: 1px solid #E5E7EB;";
    },

    playAlertSound(path) {
      new Audio(window.location.origin + path).play();
    },

    auth() {
      return new Promise((resolve, reject) => {
        frappe.auth().getLoggedInUser()
          .then((user) => { this.loggeduser = user; resolve(); })
          .catch((e) => { console.error(e); reject(e); });
      });
    },

    fetchKOT() {
      return new Promise((resolve, reject) => {
        this.call.get("ury.ury.api.ury_kot_display.kot_list", {})
          .then((result) => {
            this.branch            = result.message.Branch;
            this.kot_alert_time    = result.message.kot_alert_time;
            this.audio_alert       = result.message.audio_alert;
            this.daily_order_number = result.message.daily_order_number;
            this.kot_channel       = `kot_update_${this.branch}_${this.production}`;
            this.yangi             = result.message.YANGI           || [];
            this.tayyorlanmoqda    = result.message.TAYYORLANMOQDA  || [];
            this.tayyor            = result.message.TAYYOR          || [];
            this.updateQtyColorTable();
            this.updateTimeRemaining();
            resolve();
          })
          .catch((e) => { console.error(e); reject(e); });
      });
    },

    rotateCard(kot) {
      kot.isRotated = !kot.isRotated;
    },

    async startPreparation(kot) {
      await this.call.post("ury.ury.api.ury_kot_display.start_preparation",
        { name: kot.name, time: new Date().toLocaleTimeString() }).catch(console.error);
      this.removeAllItemsFromLocalStorage(kot);
      await this.fetchKOT();
    },

    async markReady(kot) {
      await this.call.post("ury.ury.api.ury_kot_display.mark_ready",
        { name: kot.name, time: new Date().toLocaleTimeString() }).catch(console.error);
      this.removeAllItemsFromLocalStorage(kot);
      await this.fetchKOT();
    },

    async serveOrder(kot) {
      await this.call.post("ury.ury.api.ury_kot_display.serve_kot",
        { name: kot.name, time: new Date().toLocaleTimeString() }).catch(console.error);
      this.removeAllItemsFromLocalStorage(kot);
      await this.fetchKOT();
    },

    confirmOrder(kot) {
      this.call.post("ury.ury.api.ury_kot_display.confirm_cancel_kot",
        { name: kot.name, user: this.loggeduser })
        .then(() => { this.removeAllItemsFromLocalStorage(kot); this.fetchKOT(); })
        .catch(console.error);
    },

    orderDelayNotify(kot) {
      this.call.post("ury.ury.api.ury_kot_notification.order_delay_notification",
        { id: kot.name }).catch(console.error);
    },

    updateQtyColorTable() {
      [...this.yangi, ...this.tayyorlanmoqda, ...this.tayyor].forEach((kot) => {
        kot.tableortakeaway = (!kot.restaurant_table || kot.table_takeaway == 1) ? "Takeaway" : kot.restaurant_table;
        (kot.kot_items || []).forEach((item) => {
          item.qty = item.quantity;
          if (this.isCancelled(kot)) item.qty = item.quantity - item.cancelled_qty;
        });
      });
    },

    updateTimeRemaining() {
      [...this.yangi, ...this.tayyorlanmoqda, ...this.tayyor].forEach((kot) => {
        kot.timeRemaining = this.calculateTimeRemaining(kot.time);
        const [h, m] = kot.timeRemaining.split(" : ");
        const mins = parseInt(h) * 60 + parseInt(m);
        if (mins === this.kot_alert_time && !this.isCancelled(kot)) this.orderDelayNotify(kot);
        kot.timecolor = mins >= this.kot_alert_time ? "#DC2626" : "#111827";
      });
    },

    calculateTimeRemaining(targetTime) {
      const now = new Date();
      const [h, m, s] = targetTime.split(":");
      const target = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, s);
      const diff = now - target;
      return `${Math.floor(diff / 3600000)} : ${Math.floor((diff % 3600000) / 60000)}`;
    },

    removeAllItemsFromLocalStorage(kot) {
      Object.keys(localStorage).forEach((k) => {
        if (k.startsWith(`${kot.name}_`)) localStorage.removeItem(k);
      });
    },

    redirectToLogin() {
      window.location.href = `${window.location.origin}/login?redirect-to=URYMosaic/${this.production}`;
    },

    hideAudioAlertMessage() { this.showAudioAlertMessage = false; },
    handleOnline() {
      this.isOnline = true; this.setStatusMessage("You are online");
      this.hideStatusMessageAfterDelay(); this.fetchKOT();
    },
    handleOffline() { this.isOnline = false; this.setStatusMessage("You are Offline"); },
    setStatusMessage(msg) { this.statusMessage = msg; },
    hideStatusMessageAfterDelay() { setTimeout(() => { this.statusMessage = ""; }, 3000); },
  },

  async mounted() {
    window.addEventListener("online", this.handleOnline);
    window.addEventListener("offline", this.handleOffline);
    document.addEventListener("click", this.hideAudioAlertMessage);

    const parts = window.location.href.split("/");
    this.production = decodeURIComponent(parts[parts.length - 1]);

    try {
      await this.auth();
      await this.fetchKOT();
      if (this.audio_alert === 1) this.showAudioAlertMessage = true;

      // Socket: socketni to'g'ri await qilib o'rnatish
      const sock = await initializeSocket();
      if (sock && this.kot_channel) {
        sock.on(this.kot_channel, (doc) => {
          if (this.audio_alert === 1 && doc.audio_file) this.playAlertSound(doc.audio_file);
          this.fetchKOT();
          if (doc.kot?.time) localStorage.setItem("kot_time", doc.kot.time);
        });
      }

      // Polling backup: har 10 soniyada yangilanib turadi
      this._pollInterval = setInterval(() => { this.fetchKOT(); }, 10000);

    } catch (e) {
      console.error("Mount error:", e);
      this.showModal = true;
    }

    setInterval(this.updateTimeRemaining, 60000);
  },

  beforeDestroy() {
    window.removeEventListener("online", this.handleOnline);
    window.removeEventListener("offline", this.handleOffline);
    document.removeEventListener("click", this.hideAudioAlertMessage);
    if (this._pollInterval) clearInterval(this._pollInterval);
  },
};
</script>

<style scoped>
* { box-sizing: border-box; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }
</style>
