/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class RestaurantKPIDashboard extends Component {
    static template = "restaurant_suite.KPIDashboard";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            dateFrom: this._firstOfMonth(),
            dateTo: this._today(),
            data: null,
            loading: true,
            error: null,
        });
        onWillStart(async () => this.loadData());
    }

    _today() {
        return new Date().toISOString().split("T")[0];
    }

    _firstOfMonth() {
        const d = new Date();
        return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().split("T")[0];
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call("restaurant.kpi", "get_dashboard_data", [this.state.dateFrom, this.state.dateTo]);
        } catch (err) {
            this.state.error = err.message || "Failed to load dashboard data.";
        } finally {
            this.state.loading = false;
        }
    }

    async setPreset(preset) {
        const today = new Date();
        let from = new Date(today);
        if (preset === "today") {
            from = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        } else if (preset === "week") {
            const weekday = (today.getDay() + 6) % 7;
            from.setDate(today.getDate() - weekday);
        } else {
            from = new Date(today.getFullYear(), today.getMonth(), 1);
        }
        this.state.dateFrom = from.toISOString().split("T")[0];
        this.state.dateTo = this._today();
        await this.loadData();
    }

    async onDateChange(field, ev) {
        this.state[field] = ev.target.value;
        await this.loadData();
    }

    formatCurrency(value) {
        return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value || 0);
    }

    formatPct(value) {
        return `${(value || 0).toFixed(1)}%`;
    }
}

registry.category("actions").add("restaurant_suite.kpi_dashboard", RestaurantKPIDashboard);
