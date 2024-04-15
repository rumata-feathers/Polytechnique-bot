const addToCartButtons = document.querySelectorAll('.add-to-cart');
const goToCartButton = document.getElementById('go-to-cart');

addToCartButtons.forEach(button => {
  button.addEventListener('click', () => {
    button.classList.toggle('selected'); // Toggle button style

    // Add logic for quantity selection here (example using innerHTML)
    if (button.classList.contains('selected')) {
      button.innerHTML = `
        <span class="quantity-selector">
          <button>-</button>
          <span>1</span>
          <button>+</button>
        </span>
      `;
    } else {
      button.innerHTML = 'Add to Cart';
    }

    // Enable "Go to Cart" button when at least one item is selected
    goToCartButton.disabled = !document.querySelector('.add-to-cart.selected');
  });
});