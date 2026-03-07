import { useLocation, useNavigate } from 'react-router-dom';
import { mediaUrl, type Match } from '../api/client';

export default function ResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as { result?: Record<string, unknown> } | null;

  if (!state?.result) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-700">No Results</h2>
        <p className="mt-2 text-gray-500">Upload a reference photo first to search the corpus.</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          Go to Upload
        </button>
      </div>
    );
  }

  const { session_id, total_results, timeline } = state.result as {
    session_id: string;
    total_results: number;
    timeline?: { days: Array<{ entries: Array<{ image_path: string; similarity_score: number; timestamp?: string; location_name?: string }> }> };
  };

  // Flatten timeline entries into a results list
  const results: Array<{ image_path: string; similarity_score: number; timestamp?: string; location_name?: string }> = [];
  if (timeline?.days) {
    for (const day of timeline.days) {
      for (const entry of day.entries) {
        results.push(entry);
      }
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Search Results</h1>
          <p className="text-sm text-gray-500">
            Session: {session_id} — {total_results} matches found
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/timeline', { state: location.state })}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            View Timeline
          </button>
          <button
            onClick={() => navigate('/dossier', { state: location.state })}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            View Dossier
          </button>
        </div>
      </div>

      {results.length === 0 ? (
        <p className="text-gray-500">No matching photos found.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {results.map((r, i) => (
            <div key={i} className="bg-white rounded-lg shadow overflow-hidden">
              <div className="aspect-square bg-gray-100">
                <img
                  src={mediaUrl(r.image_path)}
                  alt={`Match ${i + 1}`}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </div>
              <div className="p-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-medium text-blue-600">
                    {(r.similarity_score * 100).toFixed(0)}% match
                  </span>
                </div>
                {r.timestamp && (
                  <p className="text-xs text-gray-400 mt-0.5 truncate">
                    {new Date(r.timestamp).toLocaleDateString()}
                  </p>
                )}
                {r.location_name && (
                  <p className="text-xs text-gray-400 truncate">{r.location_name}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
