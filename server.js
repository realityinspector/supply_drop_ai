app.post('/resource-finder', async (req, res) => {
  try {
    if (!req.body.question) {
      throw new Error('Question is required');
    }
    // ... rest of handler code
  } catch (error) {
    console.error('Resource Finder Error:', error);
    res.status(400).json({ error: error.message });
  }
}); 