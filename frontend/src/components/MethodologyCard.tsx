import { ArrowRight } from 'lucide-react';
import type { Methodology } from '../types';

interface MethodologyCardProps {
  methodology: Methodology;
  onSelect: () => void;
}

export function MethodologyCard({ methodology, onSelect }: MethodologyCardProps) {
  // Determine risk level based on fragility score
  const getRiskLevel = (score: number) => {
    if (score < 0.4) return { label: 'Low Risk', color: 'bg-risk-low text-white' };
    if (score < 0.6) return { label: 'Moderate Risk', color: 'bg-risk-moderate text-white' };
    if (score < 0.8) return { label: 'High Risk', color: 'bg-risk-high text-white' };
    return { label: 'Very High Risk', color: 'bg-risk-critical text-white' };
  };

  const risk = getRiskLevel(methodology.fragility_score);

  return (
    <div
      onClick={onSelect}
      className="bg-white rounded-lg shadow-md p-6 cursor-pointer transition-all hover:shadow-lg hover:scale-105 border-2 border-transparent hover:border-blue-500"
    >
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-xl font-semibold text-gray-900">{methodology.name}</h3>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${risk.color}`}>
          {risk.label}
        </span>
      </div>

      <p className="text-gray-600 mb-4 line-clamp-3">{methodology.description}</p>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">
          Fragility: {methodology.fragility_score.toFixed(2)}
        </span>
        <button className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium">
          Select
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
