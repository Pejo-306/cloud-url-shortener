const fs = require('fs');
const path = require('path');

module.exports = (req, res, next) => {
  // Check if this is an error route (matches the rewritten URLs from routes.json)
  const errorRouteMatch = req.url.match(/^\/shorten-(\d+)$/);
  if (errorRouteMatch) {
    const statusCode = parseInt(errorRouteMatch[1]);
    const dbPath = path.join(__dirname, 'db.json');
    const dbData = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
    const dataKey = `shorten-${statusCode}`;

    if (dbData[dataKey]) {
      res.status(statusCode).json(dbData[dataKey]);
      return; // Don't continue to the next middleware
    }
  }

  // For all other requests, continue normally
  next();
};