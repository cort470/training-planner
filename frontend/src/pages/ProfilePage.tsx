import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { profileFormSchema, type ProfileFormData } from '../utils/validationSchemas';
import { formDataToUserProfile, calculateWeeksToRace } from '../utils/profileHelpers';
import { useProfileStore } from '../store/profileStore';

export function ProfilePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { selectedMethodology, setSelectedMethodology, setUserProfile } = useProfileStore();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      hrv_trend: 'unknown',
      recent_illness: false,
      menstrual_cycle_phase: 'not_applicable',
      priority_level: 'B',
      available_training_days: 6,
      max_session_duration_hours: 2.5,
      injury_status: false,
    },
  });

  // Get methodology from navigation state
  useEffect(() => {
    if (location.state?.methodology) {
      setSelectedMethodology(location.state.methodology);
    } else if (!selectedMethodology) {
      // No methodology selected, redirect to home
      navigate('/');
    }
  }, [location.state, selectedMethodology, setSelectedMethodology, navigate]);

  // Watch fields for conditional rendering
  const injuryStatus = watch('injury_status');
  const primaryGoal = watch('primary_goal');
  const raceDate = watch('race_date');

  // Auto-calculate weeks_to_race when race_date changes
  useEffect(() => {
    if (raceDate) {
      const weeks = calculateWeeksToRace(raceDate);
      setValue('weeks_to_race', weeks);
    }
  }, [raceDate, setValue]);

  const onSubmit = (data: ProfileFormData) => {
    const userProfile = formDataToUserProfile(data);
    setUserProfile(userProfile);
    navigate('/validation');
  };

  if (!selectedMethodology) {
    return null; // Will redirect in useEffect
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to methodologies
          </button>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Build Your Profile</h1>
          <p className="text-lg text-gray-600">
            Selected methodology: <span className="font-semibold">{selectedMethodology.name}</span>
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-lg shadow-md p-8 space-y-8">
          {/* Basic Information */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Basic Information</h2>
            <div className="space-y-4">
              <div>
                <label htmlFor="athlete_id" className="block text-sm font-medium text-gray-700 mb-1">
                  Athlete ID <span className="text-red-500">*</span>
                </label>
                <input
                  {...register('athlete_id')}
                  type="text"
                  id="athlete_id"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., john_doe_2026"
                />
                {errors.athlete_id && (
                  <p className="mt-1 text-sm text-red-600">{errors.athlete_id.message}</p>
                )}
              </div>
            </div>
          </section>

          {/* Current State */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Current State</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="sleep_hours" className="block text-sm font-medium text-gray-700 mb-1">
                  Average Sleep (hours/night) <span className="text-red-500">*</span>
                </label>
                <input
                  {...register('sleep_hours', { valueAsNumber: true })}
                  type="number"
                  step="0.5"
                  id="sleep_hours"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="7.5"
                />
                {errors.sleep_hours && (
                  <p className="mt-1 text-sm text-red-600">{errors.sleep_hours.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="weekly_volume_hours" className="block text-sm font-medium text-gray-700 mb-1">
                  Weekly Training Volume (hours) <span className="text-red-500">*</span>
                </label>
                <input
                  {...register('weekly_volume_hours', { valueAsNumber: true })}
                  type="number"
                  step="0.5"
                  id="weekly_volume_hours"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="10"
                />
                {errors.weekly_volume_hours && (
                  <p className="mt-1 text-sm text-red-600">{errors.weekly_volume_hours.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="stress_level" className="block text-sm font-medium text-gray-700 mb-1">
                  Stress Level <span className="text-red-500">*</span>
                </label>
                <select
                  {...register('stress_level')}
                  id="stress_level"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="low">Low</option>
                  <option value="moderate">Moderate</option>
                  <option value="high">High</option>
                </select>
                {errors.stress_level && (
                  <p className="mt-1 text-sm text-red-600">{errors.stress_level.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="volume_consistency_weeks" className="block text-sm font-medium text-gray-700 mb-1">
                  Weeks at Current Volume
                </label>
                <input
                  {...register('volume_consistency_weeks', { valueAsNumber: true })}
                  type="number"
                  id="volume_consistency_weeks"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="8"
                />
                {errors.volume_consistency_weeks && (
                  <p className="mt-1 text-sm text-red-600">{errors.volume_consistency_weeks.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="hrv_trend" className="block text-sm font-medium text-gray-700 mb-1">
                  HRV Trend
                </label>
                <select
                  {...register('hrv_trend')}
                  id="hrv_trend"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="unknown">Unknown</option>
                  <option value="increasing">Increasing</option>
                  <option value="stable">Stable</option>
                  <option value="decreasing">Decreasing</option>
                </select>
              </div>

              <div>
                <label htmlFor="menstrual_cycle_phase" className="block text-sm font-medium text-gray-700 mb-1">
                  Menstrual Cycle Phase
                </label>
                <select
                  {...register('menstrual_cycle_phase')}
                  id="menstrual_cycle_phase"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="not_applicable">Not Applicable</option>
                  <option value="follicular">Follicular</option>
                  <option value="ovulation">Ovulation</option>
                  <option value="luteal">Luteal</option>
                  <option value="menstruation">Menstruation</option>
                </select>
              </div>

              <div className="flex items-center">
                <input
                  {...register('injury_status')}
                  type="checkbox"
                  id="injury_status"
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label htmlFor="injury_status" className="ml-2 text-sm font-medium text-gray-700">
                  Currently injured
                </label>
              </div>

              <div className="flex items-center">
                <input
                  {...register('recent_illness')}
                  type="checkbox"
                  id="recent_illness"
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label htmlFor="recent_illness" className="ml-2 text-sm font-medium text-gray-700">
                  Recent illness (last 14 days)
                </label>
              </div>
            </div>

            {injuryStatus && (
              <div className="mt-4">
                <label htmlFor="injury_details" className="block text-sm font-medium text-gray-700 mb-1">
                  Injury Details <span className="text-red-500">*</span>
                </label>
                <textarea
                  {...register('injury_details')}
                  id="injury_details"
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Describe your injury..."
                />
                {errors.injury_details && (
                  <p className="mt-1 text-sm text-red-600">{errors.injury_details.message}</p>
                )}
              </div>
            )}
          </section>

          {/* Training History */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Training History</h2>
            <div>
              <label htmlFor="years_training" className="block text-sm font-medium text-gray-700 mb-1">
                Years of Consistent Training
              </label>
              <input
                {...register('years_training', { valueAsNumber: true })}
                type="number"
                step="0.5"
                id="years_training"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="2.5"
              />
              {errors.years_training && (
                <p className="mt-1 text-sm text-red-600">{errors.years_training.message}</p>
              )}
            </div>
          </section>

          {/* Goals */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Goals</h2>
            <div className="space-y-4">
              <div>
                <label htmlFor="primary_goal" className="block text-sm font-medium text-gray-700 mb-1">
                  Primary Goal <span className="text-red-500">*</span>
                </label>
                <select
                  {...register('primary_goal')}
                  id="primary_goal"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Select a goal...</option>
                  <option value="race_performance">Race Performance</option>
                  <option value="base_building">Base Building</option>
                  <option value="weight_loss">Weight Loss</option>
                  <option value="general_fitness">General Fitness</option>
                  <option value="injury_prevention">Injury Prevention</option>
                </select>
                {errors.primary_goal && (
                  <p className="mt-1 text-sm text-red-600">{errors.primary_goal.message}</p>
                )}
              </div>

              {primaryGoal === 'race_performance' && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="race_date" className="block text-sm font-medium text-gray-700 mb-1">
                        Race Date <span className="text-red-500">*</span>
                      </label>
                      <input
                        {...register('race_date')}
                        type="date"
                        id="race_date"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      {errors.race_date && (
                        <p className="mt-1 text-sm text-red-600">{errors.race_date.message}</p>
                      )}
                    </div>

                    <div>
                      <label htmlFor="race_distance" className="block text-sm font-medium text-gray-700 mb-1">
                        Race Distance <span className="text-red-500">*</span>
                      </label>
                      <select
                        {...register('race_distance')}
                        id="race_distance"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="">Select distance...</option>
                        <option value="sprint">Sprint</option>
                        <option value="olympic">Olympic</option>
                        <option value="half_ironman">Half Ironman</option>
                        <option value="70.3">70.3</option>
                        <option value="ironman">Ironman</option>
                        <option value="other">Other</option>
                      </select>
                      {errors.race_distance && (
                        <p className="mt-1 text-sm text-red-600">{errors.race_distance.message}</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <label htmlFor="priority_level" className="block text-sm font-medium text-gray-700 mb-1">
                      Race Priority
                    </label>
                    <select
                      {...register('priority_level')}
                      id="priority_level"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="A">A (Key Race)</option>
                      <option value="B">B (Important)</option>
                      <option value="C">C (Training Race)</option>
                    </select>
                  </div>
                </>
              )}
            </div>
          </section>

          {/* Constraints */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Constraints</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="available_training_days" className="block text-sm font-medium text-gray-700 mb-1">
                  Available Training Days/Week
                </label>
                <input
                  {...register('available_training_days', { valueAsNumber: true })}
                  type="number"
                  id="available_training_days"
                  min="1"
                  max="7"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                {errors.available_training_days && (
                  <p className="mt-1 text-sm text-red-600">{errors.available_training_days.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="max_session_duration_hours" className="block text-sm font-medium text-gray-700 mb-1">
                  Max Session Duration (hours)
                </label>
                <input
                  {...register('max_session_duration_hours', { valueAsNumber: true })}
                  type="number"
                  step="0.5"
                  id="max_session_duration_hours"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                {errors.max_session_duration_hours && (
                  <p className="mt-1 text-sm text-red-600">{errors.max_session_duration_hours.message}</p>
                )}
              </div>
            </div>
          </section>

          {/* Preferences */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Preferences (Optional)</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="long_workout_day" className="block text-sm font-medium text-gray-700 mb-1">
                  Preferred Long Workout Day
                </label>
                <select
                  {...register('long_workout_day')}
                  id="long_workout_day"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">None selected</option>
                  <option value="saturday">Saturday</option>
                  <option value="sunday">Sunday</option>
                  <option value="monday">Monday</option>
                  <option value="tuesday">Tuesday</option>
                  <option value="wednesday">Wednesday</option>
                  <option value="thursday">Thursday</option>
                  <option value="friday">Friday</option>
                </select>
              </div>

              <div>
                <label htmlFor="rest_day" className="block text-sm font-medium text-gray-700 mb-1">
                  Preferred Rest Day
                </label>
                <select
                  {...register('rest_day')}
                  id="rest_day"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">None selected</option>
                  <option value="sunday">Sunday</option>
                  <option value="monday">Monday</option>
                  <option value="tuesday">Tuesday</option>
                  <option value="wednesday">Wednesday</option>
                  <option value="thursday">Thursday</option>
                  <option value="friday">Friday</option>
                  <option value="saturday">Saturday</option>
                </select>
              </div>
            </div>
          </section>

          {/* Submit Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Continue to Validation
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
