import { stripHtml } from '../utils/htmlStripper.js';

function formatProducts(products) {
  const formattedChildProducts = [];

  products.forEach(parentProduct => {
    const parentDetailedDescription = parentProduct.detailed_description ? stripHtml(parentProduct.detailed_description) : '';
    const parentShortDescription = parentProduct.short_description ? stripHtml(parentProduct.short_description) : '';
    const parentCategories = parentProduct.categories || [];
    const parentAiCategories = (parentProduct.ai_categories || []).map(cat => cat.categoryName);
    const combinedCategories = [...new Set([...parentCategories, ...parentAiCategories])];

    parentProduct.child_products.forEach(childProduct => {
      formattedChildProducts.push({
        description: parentDetailedDescription,
        name: childProduct.product_name,
        code: childProduct.code,
        ean_code: childProduct.ean_code,
        categories: combinedCategories,
        short_description: parentShortDescription,
      });
    });
  });

  return formattedChildProducts;
}

export { formatProducts };
