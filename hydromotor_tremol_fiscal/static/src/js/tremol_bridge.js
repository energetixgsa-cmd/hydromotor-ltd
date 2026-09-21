/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

function xmlEscape(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll('"', "&quot;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

function commandXml(name, args = {}) {
    const body = Object.entries(args)
        .map(([key, value]) => `<Arg Name="${xmlEscape(key)}" Value="${xmlEscape(value)}" />`)
        .join("");
    return `<?xml version="1.0" encoding="UTF-8"?><Command Name="${xmlEscape(name)}"><Args>${body}</Args></Command>`;
}

function responseError(text) {
    const code = text.match(/<Res\b[^>]*\bCode=["']([^"']+)["']/i)?.[1];
    if ((code && code !== "0") || /<Err\b/i.test(text)) {
        const message = text.match(/<Message>([\s\S]*?)<\/Message>/i)?.[1];
        return message || `ZFPLabServer error ${code || "unknown"}`;
    }
    return false;
}

async function postXml(url, xml) {
    let response;
    try {
        response = await fetch(url, {
            method: "POST",
            mode: "cors",
            cache: "no-store",
            headers: { "Content-Type": "text/plain;charset=UTF-8" },
            body: xml,
        });
    } catch (error) {
        throw new Error(
            `ZFPLabServer is not reachable at ${url}. ` +
                "Check that it is running and that the browser allows access to localhost. " +
                `Details: ${error.message}`
        );
    }
    const text = await response.text();
    if (!response.ok) {
        throw new Error(`ZFPLabServer HTTP ${response.status}: ${text}`);
    }
    const error = responseError(text);
    if (error) {
        throw new Error(error);
    }
    return text;
}

async function initialize(config) {
    return postXml(
        config.server_url,
        commandXml("Settings", {
            com: config.com_port,
            baud: config.baud_rate,
            tcp: 0,
            ip: "",
            port: "",
            password: "",
            keepPortOpen: config.keep_port_open ? 1 : 0,
        })
    );
}

async function sendCommand(config, name, args = {}) {
    return postXml(config.server_url, commandXml(name, args));
}

function receiptNumber(responseText, fallback) {
    const document = new DOMParser().parseFromString(responseText, "application/xml");
    for (const name of ["RcpNum", "ReceiptNum", "ReceiptNumber", "LastReceiptNum"]) {
        const node = document.querySelector(`[Name="${name}"]`);
        if (node) {
            return node.getAttribute("Value") || node.textContent || fallback;
        }
    }
    return fallback;
}

export class TremolBridgeAction extends Component {
    static template = "hydromotor_tremol_fiscal.BridgeAction";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.state = useState({ status: "Connecting to TREMOL…", error: false });
        onWillStart(() => this.run());
    }

    async run() {
        const params = this.props.action.params || {};
        try {
            if (params.operation === "test") {
                await this.runTest(params);
            } else if (params.operation === "issue") {
                await this.runIssue(params.payload);
            } else {
                throw new Error("Unknown TREMOL operation.");
            }
            await this.action.doAction({ type: "ir.actions.act_window_close" });
        } catch (error) {
            this.state.error = true;
            this.state.status = error.message || String(error);
            this.notification.add(this.state.status, {
                title: "TREMOL",
                type: "danger",
                sticky: true,
            });
        }
    }

    async runTest(params) {
        this.state.status = "Initializing COM connection…";
        const settingsResponse = await initialize(params.config);
        this.state.status = "Reading device status…";
        const statusResponse = await sendCommand(params.config, "ReadStatus");
        const raw = `${settingsResponse}\n${statusResponse}`;
        await this.orm.call("account.move", "tremol_record_test", [params.move_id, raw]);
        this.notification.add("TREMOL M23 connection is working.", {
            title: "TREMOL",
            type: "success",
        });
    }

    async runIssue(payload) {
        const config = payload.config;
        const responses = [];
        let receiptOpened = false;
        try {
            this.state.status = "Initializing COM connection…";
            responses.push(await initialize(config));
            responses.push(await sendCommand(config, "ReadStatus"));

            this.state.status = "Opening fiscal receipt…";
            responses.push(
                await sendCommand(config, "OpenReceipt", {
                    OperNum: config.operator_number,
                    OperPass: config.operator_password,
                    RcpFormat: 1,
                    PrintVAT: 1,
                    FiscalRcpPrintType: 0,
                    UniqueReceiptNumber: payload.unique_receipt_number,
                })
            );
            receiptOpened = true;

            for (const item of payload.items) {
                this.state.status = `Printing ${item.name}…`;
                responses.push(
                    await sendCommand(config, "SellPLUwithSpecifiedVAT", {
                        NamePLU: item.name,
                        OptionVATClass: item.vat_group,
                        Price: item.price,
                        Quantity: item.quantity,
                        DiscAddP: "",
                        DiscAddV: "",
                    })
                );
            }

            this.state.status = "Registering payment…";
            responses.push(
                await sendCommand(config, "Payment", {
                    PaymentType: payload.payment_code,
                    OptionChange: 1,
                    Amount: payload.amount_total,
                    OptionChangeType: 1,
                })
            );
            this.state.status = "Closing fiscal receipt…";
            const closeResponse = await sendCommand(config, "CloseReceipt");
            responses.push(closeResponse);
            receiptOpened = false;

            const raw = responses.join("\n");
            const number = receiptNumber(closeResponse, payload.unique_receipt_number);
            await this.orm.call("account.move", "tremol_record_result", [
                payload.move_id,
                true,
                raw,
                number,
            ]);
            this.notification.add(`Fiscal receipt issued: ${number}`, {
                title: "TREMOL",
                type: "success",
                sticky: true,
            });
        } catch (error) {
            if (receiptOpened) {
                try {
                    responses.push(await sendCommand(config, "CancelReceipt"));
                } catch (cancelError) {
                    responses.push(`CancelReceipt failed: ${cancelError.message}`);
                }
            }
            responses.push(`ERROR: ${error.message || String(error)}`);
            await this.orm.call("account.move", "tremol_record_result", [
                payload.move_id,
                false,
                responses.join("\n"),
                false,
            ]);
            throw error;
        }
    }
}

registry.category("actions").add("hydromotor_tremol_fiscal.bridge", TremolBridgeAction);

