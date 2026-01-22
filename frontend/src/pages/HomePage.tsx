import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useMethodologies } from '../hooks/useMethodologies';
import { MethodologyCard } from '../components/MethodologyCard';

export function HomePage() {
  const navigate = useNavigate();
  const { data: methodologies, isLoading, error } = useMethodologies();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-red-600 mb-2">Error Loading Methodologies</h2>
          <p className="text-gray-600">
            {error instanceof Error ? error.message : 'Failed to load methodologies'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Choose Your Training Methodology
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Select a scientifically-backed training methodology that matches your goals,
            experience level, and current fitness state.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {methodologies?.map((methodology) => (
            <MethodologyCard
              key={methodology.id}
              methodology={methodology}
              onSelect={() => navigate('/profile', { state: { methodology } })}
            />
          ))}
        </div>

        {methodologies?.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-600">No methodologies available</p>
          </div>
        )}
      </div>
    </div>
  );
}
