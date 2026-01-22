import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, AlertTriangle, XCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { useProfileStore } from '../store/profileStore';
import { useValidation } from '../hooks/useValidation';

export function ValidationPage() {
  const navigate = useNavigate();
  const { selectedMethodology, userProfile, validationResult, setValidationResult } = useProfileStore();
  const { mutate: validate, isPending, isError, error } = useValidation();
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    assumptions: false,
    safetyGates: false,
    reasoningTrace: false,
  });

  useEffect(() => {
    if (!selectedMethodology || !userProfile) {
      navigate('/');
      return;
    }

    // If we don't have a validation result yet, trigger validation
    if (!validationResult) {
      validate(
        {
          userProfile,
          methodologyId: selectedMethodology.id,
        },
        {
          onSuccess: (data) => {
            setValidationResult(data);
          },
        }
      );
    }
  }, [selectedMethodology, userProfile, validationResult, validate, setValidationResult, navigate]);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  if (!selectedMethodology || !userProfile) {
    return null;
  }

  if (isPending) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Validating Your Profile</h2>
          <p className="text-gray-600">
            Checking your profile against {selectedMethodology.name} methodology requirements...
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
            onClick={() => navigate('/profile')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to profile
          </button>
          <div className="bg-white rounded-lg shadow-md p-8">
            <div className="flex items-center gap-3 mb-4">
              <XCircle className="w-8 h-8 text-red-600" />
              <h2 className="text-2xl font-bold text-gray-900">Validation Error</h2>
            </div>
            <p className="text-gray-600 mb-4">
              {error instanceof Error ? error.message : 'Failed to validate profile'}
            </p>
            <button
              onClick={() => navigate('/profile')}
              className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700"
            >
              Return to Profile
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!validationResult) {
    return null;
  }

  const { approved, reasoning_trace } = validationResult;
  const hasWarnings = reasoning_trace.warnings && reasoning_trace.warnings.length > 0;
  const hasBlockingViolations =
    reasoning_trace.blocking_violations && reasoning_trace.blocking_violations.length > 0;

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/profile')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to profile
          </button>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Validation Results</h1>
          <p className="text-lg text-gray-600">
            Methodology: <span className="font-semibold">{selectedMethodology.name}</span>
          </p>
        </div>

        {/* Status Card */}
        <div
          className={`bg-white rounded-lg shadow-md p-8 mb-6 border-l-4 ${
            approved && !hasWarnings
              ? 'border-green-500'
              : hasWarnings && !hasBlockingViolations
              ? 'border-yellow-500'
              : 'border-red-500'
          }`}
        >
          <div className="flex items-start gap-4">
            {approved && !hasWarnings && (
              <>
                <CheckCircle className="w-12 h-12 text-green-600 flex-shrink-0" />
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Profile Approved!</h2>
                  <p className="text-gray-600 mb-4">
                    Your profile meets all the requirements for the {selectedMethodology.name} methodology.
                    You're ready to generate your training plan.
                  </p>
                  <button
                    onClick={() => navigate('/plan')}
                    className="px-6 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700"
                  >
                    Generate Training Plan
                  </button>
                </div>
              </>
            )}

            {approved && hasWarnings && (
              <>
                <AlertTriangle className="w-12 h-12 text-yellow-600 flex-shrink-0" />
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Approved with Warnings</h2>
                  <p className="text-gray-600 mb-4">
                    Your profile is approved, but there are some considerations to be aware of. Review the
                    warnings below before proceeding.
                  </p>
                  <button
                    onClick={() => navigate('/plan')}
                    className="px-6 py-3 bg-yellow-600 text-white font-medium rounded-lg hover:bg-yellow-700"
                  >
                    Generate Training Plan
                  </button>
                </div>
              </>
            )}

            {!approved && (
              <>
                <XCircle className="w-12 h-12 text-red-600 flex-shrink-0" />
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Profile Not Approved</h2>
                  <p className="text-gray-600 mb-4">
                    Your profile does not meet the safety requirements for the {selectedMethodology.name}{' '}
                    methodology. Please review the blocking violations below and adjust your profile or
                    consider a different methodology.
                  </p>
                  <div className="flex gap-3">
                    <button
                      onClick={() => navigate('/profile')}
                      className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700"
                    >
                      Edit Profile
                    </button>
                    <button
                      onClick={() => navigate('/')}
                      className="px-6 py-3 bg-gray-600 text-white font-medium rounded-lg hover:bg-gray-700"
                    >
                      Choose Different Methodology
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Warnings */}
        {hasWarnings && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-yellow-900 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Warnings
            </h3>
            <ul className="space-y-2">
              {reasoning_trace.warnings.map((warning, index) => (
                <li key={index} className="text-yellow-800 flex items-start gap-2">
                  <span className="font-bold mt-1">•</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Blocking Violations */}
        {hasBlockingViolations && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-red-900 mb-3 flex items-center gap-2">
              <XCircle className="w-5 h-5" />
              Blocking Violations
            </h3>
            <ul className="space-y-2">
              {reasoning_trace.blocking_violations.map((violation, index) => (
                <li key={index} className="text-red-800 flex items-start gap-2">
                  <span className="font-bold mt-1">•</span>
                  <span>{violation}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Assumptions Checked */}
        <div className="bg-white rounded-lg shadow-md mb-6">
          <button
            onClick={() => toggleSection('assumptions')}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <h3 className="text-lg font-semibold text-gray-900">Assumptions Checked</h3>
            {expandedSections.assumptions ? (
              <ChevronUp className="w-5 h-5 text-gray-600" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-600" />
            )}
          </button>
          {expandedSections.assumptions && (
            <div className="px-6 pb-4 space-y-3">
              {reasoning_trace.assumptions_checked.map((assumption, index) => (
                <div key={index} className="border-l-2 border-gray-200 pl-4 py-2">
                  <div className="flex items-start gap-2 mb-1">
                    {assumption.passed ? (
                      <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{assumption.assumption_key}</p>
                      <p className="text-sm text-gray-600 mt-1">{assumption.reasoning}</p>
                      {assumption.user_value !== null && assumption.threshold !== null && (
                        <p className="text-xs text-gray-500 mt-1">
                          Your value: {JSON.stringify(assumption.user_value)} | Threshold:{' '}
                          {JSON.stringify(assumption.threshold)}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Safety Gates */}
        <div className="bg-white rounded-lg shadow-md mb-6">
          <button
            onClick={() => toggleSection('safetyGates')}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <h3 className="text-lg font-semibold text-gray-900">Safety Gates Evaluated</h3>
            {expandedSections.safetyGates ? (
              <ChevronUp className="w-5 h-5 text-gray-600" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-600" />
            )}
          </button>
          {expandedSections.safetyGates && (
            <div className="px-6 pb-4 space-y-3">
              {reasoning_trace.safety_gates_evaluated.map((gate, index) => (
                <div key={index} className="border-l-2 border-gray-200 pl-4 py-2">
                  <div className="flex items-start gap-2 mb-1">
                    {gate.passed ? (
                      <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                    ) : gate.severity === 'blocking' ? (
                      <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-gray-900">{gate.condition}</p>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            gate.severity === 'blocking'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {gate.severity}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-1">{gate.reasoning}</p>
                      <p className="text-xs text-gray-500">Threshold: {gate.threshold}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Fragility Score */}
        {validationResult.fragility_score !== undefined && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Fragility Assessment</h3>
            <div className="flex items-center gap-4 mb-3">
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      validationResult.fragility_score < 0.4
                        ? 'bg-green-500'
                        : validationResult.fragility_score < 0.6
                        ? 'bg-yellow-500'
                        : validationResult.fragility_score < 0.8
                        ? 'bg-orange-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${validationResult.fragility_score * 100}%` }}
                  />
                </div>
              </div>
              <span className="font-bold text-lg text-gray-900">
                {(validationResult.fragility_score * 100).toFixed(0)}%
              </span>
            </div>
            {validationResult.fragility_interpretation && (
              <p className="text-sm text-gray-600">{validationResult.fragility_interpretation}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
