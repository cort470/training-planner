/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Zone colors for training intensity
        zone: {
          1: '#22c55e',  // Green - Z1 (easy)
          2: '#84cc16',  // Light green - Z2 (aerobic)
          3: '#eab308',  // Yellow - Z3 (threshold)
          4: '#f97316',  // Orange - Z4 (VO2max)
          5: '#ef4444',  // Red - Z5 (anaerobic)
        },
        // Risk level colors
        risk: {
          low: '#22c55e',
          moderate: '#eab308',
          high: '#f97316',
          critical: '#ef4444',
        },
      },
    },
  },
  plugins: [],
}
