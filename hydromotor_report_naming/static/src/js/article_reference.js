/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductNameAndDescriptionField } from "@product/product_name_and_description/product_name_and_description";
import { descriptionWithoutReference } from "./article_utils";

patch(ProductNameAndDescriptionField.prototype, {
    get label() {
        const data = this.props.record.data;
        if (!("hm_article_number" in data) || (data.display_type && data.display_type !== "product")) {
            return super.label;
        }
        let label = descriptionWithoutReference(data[this.descriptionColumn] || "", data.hm_article_number);
        const productName = this.productName;
        // Keep the native editor and configurator; change only their display value.
        if (productName && label.startsWith(productName)) {
            label = label.slice(productName.length);
        }
        return label.trim();
    },
});
