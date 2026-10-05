/**
 * Maps a catalog category to a simple emoji glyph, used as a lightweight
 * stand-in for product photography on the item cards.
 */
const ICONS = {
  outerwear: "🧥",
  top: "👕",
  bottom: "👖",
  footwear: "👟",
  bag: "👜",
  accessory: "💍",
};

export function getCategoryIcon(category) {
  return ICONS[category] || "🏷️";
}
