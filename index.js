import { formatProducts } from './src/productProcessor/formatProducts.js';

async function getAllProducts() {
  try {
    const response = await fetch('https://api.time-4-action.com/api/export/product');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    console.log('Raw API data:', data); // Add this line for debugging
    return data;
  } catch (error) {
    console.error('Error fetching data:', error);
  }
}

async function main() {
  const response = await getAllProducts(); // Get the full response object
  if (response && Array.isArray(response.data)) { // Check if response and response.data exist and response.data is an array
    const products = response.data; // Extract the actual products array
    const formatted = formatProducts(products);
    console.log(formatted);
  } else {
    console.error('Products data is not an array, cannot format.');
  }
}

main();