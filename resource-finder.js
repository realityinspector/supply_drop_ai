document.querySelector('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const response = await fetch('/resource-finder', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        apiKey: document.querySelector('#apiKey').value,
        question: document.querySelector('#question').value
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    // Handle success
  } catch (error) {
    console.error('Error:', error);
    // Display error to user
    document.querySelector('#error-message').textContent = 'An error occurred: ' + error.message;
  }
}); 