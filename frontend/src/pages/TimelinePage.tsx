import { useLocation, useNavigate } from 'react-router-dom';
import { mediaUrl } from '../api/client';

interface TimelineEntry {
  image_path: string;
  similarity_score: number;
  timestamp?: string;
  time_of_day?: string;
  location_name?: string;
  scene_label?: string;
}

interface DayGroup {
  date: string;
  entries: TimelineEntry[];
  scenes: Array<{ label: string; entries: TimelineEntry[] }>;
}

interface TimelineData {
  days: DayGroup[];
  gaps: Array<{ start: string; end: string; gap_days: number }>;
  total_entries: number;
  active_days: number;
}

export default function TimelinePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as { result?: Record<string, unknown> } | null;

  if (!state?.result) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-700">No Timeline</h2>
        <p className="mt-2 text-gray-500">Run a search first to view the timeline.</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          Go to Upload
        </button>
      </div>
    );
  }

  const timeline = state.result.timeline as TimelineData | undefined;

  if (!timeline || !timeline.days?.length) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-700">No Timeline Data</h2>
        <p className="mt-2 text-gray-500">No timestamped photos found in results.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Timeline</h1>
          <p className="text-sm text-gray-500">
            {timeline.active_days} active days — {timeline.total_entries} photos
          </p>
        </div>
        <button
          onClick={() => navigate('/dossier', { state: location.state })}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          View Dossier
        </button>
      </div>

      {/* Calendar heatmap (simplified) */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Activity Calendar</h3>
        <div className="flex flex-wrap gap-1">
          {timeline.days.map((day) => {
            const count = day.entries.length;
            const intensity =
              count >= 10 ? 'bg-blue-700' :
              count >= 5 ? 'bg-blue-500' :
              count >= 2 ? 'bg-blue-300' :
              'bg-blue-100';
            return (
              <div
                key={day.date}
                className={`w-6 h-6 rounded ${intensity} cursor-pointer`}
                title={`${day.date}: ${count} photos`}
              />
            );
          })}
        </div>
      </div>

      {/* Gap annotations */}
      {timeline.gaps && timeline.gaps.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <h3 className="text-sm font-medium text-amber-800">Gaps Detected</h3>
          <ul className="mt-1 text-sm text-amber-700 space-y-0.5">
            {timeline.gaps.map((gap, i) => (
              <li key={i}>
                No photos {gap.start} — {gap.end} ({gap.gap_days} days)
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Day-by-day timeline */}
      <div className="space-y-8">
        {timeline.days.map((day) => (
          <div key={day.date}>
            <h2 className="text-lg font-semibold text-gray-800 sticky top-0 bg-gray-50 py-2 z-10 border-b border-gray-200">
              {new Date(day.date + 'T00:00:00').toLocaleDateString(undefined, {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
              <span className="ml-2 text-sm font-normal text-gray-500">
                {day.entries.length} photos
              </span>
            </h2>

            <div className="mt-3 flex gap-3 overflow-x-auto pb-2">
              {day.entries.map((entry, i) => (
                <div key={i} className="flex-shrink-0 w-40">
                  <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                    <img
                      src={mediaUrl(entry.image_path)}
                      alt={`${day.date} photo ${i + 1}`}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                  <div className="mt-1">
                    {entry.time_of_day && (
                      <span className="text-xs text-gray-500">{entry.time_of_day}</span>
                    )}
                    {entry.location_name && (
                      <p className="text-xs text-gray-400 truncate">{entry.location_name}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
