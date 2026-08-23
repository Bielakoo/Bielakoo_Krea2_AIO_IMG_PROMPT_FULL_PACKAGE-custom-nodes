import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

function ensureResultWidget(node) {
    let widget = node.widgets?.find((w) => w.name === "result");
    if (!widget) {
        widget = ComfyWidgets.STRING(
            node,
            "result",
            ["STRING", { multiline: true, default: "Run / Queue the workflow to calculate a recommendation." }],
            app
        ).widget;
        widget.serialize = false;
        if (widget.inputEl) {
            widget.inputEl.readOnly = true;
            widget.inputEl.style.minHeight = "118px";
        }
    }
    return widget;
}

app.registerExtension({
    name: "Bielakoo.AIOResolutionCalculatorDisplay",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "BielakooAIOResolutionCalculator") return;

        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            const widget = ensureResultWidget(this);
            if (!widget.value) widget.value = "Run / Queue the workflow to calculate a recommendation.";
            this.setSize([Math.max(this.size[0], 500), Math.max(this.size[1], 320)]);
            return result;
        };

        const originalExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            originalExecuted?.apply(this, arguments);
            const raw = message?.text;
            const text = Array.isArray(raw)
                ? raw.join("\n")
                : (raw ?? "Calculator executed, but no result text was returned.");
            const widget = ensureResultWidget(this);
            widget.value = text;
            if (widget.inputEl) {
                widget.inputEl.value = text;
                widget.inputEl.readOnly = true;
            }
            this.setSize([Math.max(this.size[0], 500), Math.max(this.size[1], 360)]);
            app.graph.setDirtyCanvas(true, true);
        };
    },
});
