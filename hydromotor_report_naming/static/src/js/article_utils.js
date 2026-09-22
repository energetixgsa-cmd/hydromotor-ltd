/** @odoo-module **/
export function descriptionWithoutReference(description, reference) {
    if (!description || !reference) return description;
    const prefix = `[${reference}] `;
    return description.startsWith(prefix) ? description.slice(prefix.length) : description;
}
