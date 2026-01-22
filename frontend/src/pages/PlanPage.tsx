import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Calendar, Loader2, Download } from 'lucide-react';
import { useProfileStore } from '../store/profileStore';
import { usePlanGeneration } from '../hooks/usePlanGeneration';

export function PlanPage() {
  const navigate = useNavigate();
  const { selectedMethodology, userProfile, trainingPlan, setTrainingPlan } = useProfileStore();
  const { mutate: generatePlan, isPending, isError, error } = usePlanGeneration();

  useEffect(() => {
    if (!selectedMethodology || !userProfile) {
      navigate('/');
      return;
    }

    // If we don't have a training plan yet, generate one
    if (!trainingPlan) {
      generatePlan(
        {
          userProfile,
          methodologyId: selectedMethodology.id,
        },
        {
          onSuccess: (data) => {
            setTrainingPlan(data.plan);
          },
        }
      );
    }
  }, [selectedMethodology, userProfile, trainingPlan, generatePlan, setTrainingPlan, navigate]);

  if (!selectedMethodology || !userProfile) {
    return null;
  }

  if (isPending) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Generating Your Training Plan</h2>
          <p className="text-gray-600">
            Creating a personalized {trainingPlan?.total_weeks || 12}-week plan with{' '}
            {selectedMethodology.name}...
          </p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-gray-50 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <button
            onClick={() => navigate('/validation')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to validation
          </button>
          <div className="bg-white rounded-lg shadow-md p-8">
            <div className="flex items-center gap-3 mb-4">
              <Calendar className="w-8 h-8 text-red-600" />
              <h2 className="text-2xl font-bold text-gray-900">Plan Generation Error</h2>
            </div>
            <p className="text-gray-600 mb-4">
              {error instanceof Error ? error.message : 'Failed to generate training plan'}
            </p>
            <button
              onClick={() => navigate('/validation')}
              className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700"
            >
              Return to Validation
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!trainingPlan) {
    return null;
  }

  const getPhaseColor = (phase: string) => {
    const phaseLower = phase.toLowerCase();
    if (phaseLower.includes('base')) return 'bg-blue-100 text-blue-800 border-blue-200';
    if (phaseLower.includes('build')) return 'bg-green-100 text-green-800 border-green-200';
    if (phaseLower.includes('peak')) return 'bg-orange-100 text-orange-800 border-orange-200';
    if (phaseLower.includes('taper')) return 'bg-purple-100 text-purple-800 border-purple-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const getZoneColor = (zone: string) => {
    if (zone.includes('1') || zone.includes('2')) return 'text-green-700 bg-green-50';
    if (zone.includes('3')) return 'text-yellow-700 bg-yellow-50';
    if (zone.includes('4') || zone.includes('5')) return 'text-orange-700 bg-orange-50';
    return 'text-gray-700 bg-gray-50';
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours === 0) return `${mins}min`;
    if (mins === 0) return `${hours}h`;
    return `${hours}h ${mins}min`;
  };

  const totalVolume = trainingPlan.weeks.reduce(
    (sum, week) => sum + week.weekly_volume_minutes,
    0
  );
  const avgWeeklyVolume = totalVolume / trainingPlan.weeks.length;

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/validation')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to validation
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">Your Training Plan</h1>
              <p className="text-lg text-gray-600">
                {trainingPlan.total_weeks}-week {selectedMethodology.name} plan for{' '}
                {userProfile.athlete_id}
              </p>
            </div>
            <button
              onClick={() => {
                const dataStr = JSON.stringify(trainingPlan, null, 2);
                const dataBlob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(dataBlob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `training-plan-${trainingPlan.plan_id}.json`;
                link.click();
              }}
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              <Download className="w-4 h-4" />
              Export JSON
            </button>
          </div>
        </div>

        {/* Plan Summary */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Plan Summary</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-600">Total Weeks</p>
              <p className="text-2xl font-bold text-gray-900">{trainingPlan.total_weeks}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Avg Weekly Volume</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatDuration(Math.round(avgWeeklyVolume))}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Volume</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatDuration(totalVolume)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Methodology</p>
              <p className="text-lg font-semibold text-gray-900">{selectedMethodology.name}</p>
            </div>
          </div>
          {trainingPlan.race_date && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-900">
                Race Date: {new Date(trainingPlan.race_date).toLocaleDateString()}
              </p>
            </div>
          )}
        </div>

        {/* Weekly Calendar */}
        <div className="space-y-6">
          <h2 className="text-2xl font-semibold text-gray-900">Weekly Schedule</h2>
          {trainingPlan.weeks.map((week) => (
            <div key={week.week_number} className="bg-white rounded-lg shadow-md overflow-hidden">
              {/* Week Header */}
              <div className="bg-gray-800 text-white px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <h3 className="text-xl font-bold">Week {week.week_number}</h3>
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-medium border ${getPhaseColor(
                      week.phase
                    )}`}
                  >
                    {week.phase}
                  </span>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-300">Weekly Volume</p>
                  <p className="text-lg font-semibold">
                    {formatDuration(week.weekly_volume_minutes)}
                  </p>
                </div>
              </div>

              {/* Sessions Grid */}
              <div className="p-6">
                {week.sessions.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">Rest Week</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {week.sessions.map((session, index) => (
                      <div
                        key={index}
                        className="border border-gray-200 rounded-lg p-4 hover:border-blue-400 transition-colors"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <p className="text-xs text-gray-500 uppercase font-medium">
                              {session.day_of_week}
                            </p>
                            <p className="font-semibold text-gray-900 mt-1">
                              {session.session_type}
                            </p>
                          </div>
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${getZoneColor(
                              session.primary_zone
                            )}`}
                          >
                            {session.primary_zone}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                          {session.description}
                        </p>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <Calendar className="w-3 h-3" />
                          <span>{formatDuration(session.duration_minutes)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Footer Actions */}
        <div className="mt-8 flex justify-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="px-6 py-3 bg-gray-600 text-white font-medium rounded-lg hover:bg-gray-700"
          >
            Create Another Plan
          </button>
        </div>
      </div>
    </div>
  );
}
