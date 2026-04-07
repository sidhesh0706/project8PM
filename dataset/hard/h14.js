function normalizeEventType(eventType) {
  if (!eventType) {
    return "unknown";
  }
  return String(eventType).trim().toLowerCase();
}

module.exports = { normalizeEventType };
