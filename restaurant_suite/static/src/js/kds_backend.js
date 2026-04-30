/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class RestaurantKDSBackend extends Component {
    static template = "restaurant_suite.KDSBackend";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            orders: [],
            stationName: "",
            stationId: this._resolveStationId(),
            lastRefresh: null,
            loading: true,
        });
        this._interval = null;

        onMounted(async () => {
            await this.loadStation();
            await this.refreshOrders();
            this._interval = setInterval(() => this.refreshOrders(), 10000);
        });

        onWillUnmount(() => {
            if (this._interval) {
                clearInterval(this._interval);
            }
        });
    }

    _resolveStationId() {
        const ctx = this.props?.action?.context || {};
        return Number(ctx.stationId || 0) || 0;
    }

    async loadStation() {
        if (!this.state.stationId) {
            this.state.stationName = "All Stations";
            return;
        }
        const stations = await this.orm.read("restaurant.kds.station", [this.state.stationId], ["name"]);
        this.state.stationName = stations.length ? stations[0].name : "Unknown Station";
    }

    async refreshOrders() {
        const stationId = this.state.stationId;
        if (!stationId) {
            this.state.orders = [];
            this.state.loading = false;
            this.state.lastRefresh = new Date().toLocaleTimeString();
            return;
        }
        this.state.orders = await this.orm.call("restaurant.kds.order", "get_pending_for_station", [stationId]);
        this.state.lastRefresh = new Date().toLocaleTimeString();
        this.state.loading = false;
    }

    async markPreparing(kdsId) {
        await this.orm.call("restaurant.kds.order", "action_mark_preparing", [[kdsId]]);
        await this.refreshOrders();
    }

    async markReady(kdsId) {
        await this.orm.call("restaurant.kds.order", "action_mark_ready", [[kdsId]]);
        this.notification.add("Marked ready", { type: "success" });
        await this.refreshOrders();
    }

    getElapsedMinutes(sentAt) {
        if (!sentAt) return 0;
        return Math.floor((Date.now() - new Date(sentAt).getTime()) / 60000);
    }

    getUrgency(sentAt) {
        const minutes = this.getElapsedMinutes(sentAt);
        if (minutes >= 20) return "urgent";
        if (minutes >= 10) return "warning";
        return "normal";
    }
}

registry.category("actions").add("restaurant_suite.kds_backend", RestaurantKDSBackend);
