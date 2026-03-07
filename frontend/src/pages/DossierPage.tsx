import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { mediaUrl, type Dossier } from '../api/client';

export default function DossierPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as { result?: Record<string, unknown> } | null;
  const [expandedDay, setExpandedDay] = useState<string | null>(null);

  if (!state?.result) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-700">No Dossier</h2>
        <p className="mt-2 text-gray-500">Run a full pipeline search to generate a dossier.</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          Go to Upload
        </button>
      </div>
    );
  }

  const dossier = state.result.dossier as Dossier | undefined;
  const patterns = state.result.patterns as Array<{ pattern_type: string; description: string; confidence: number }> | undefined;

  if (!dossier) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-700">No Narrative Generated</h2>
        <p className="mt-2 text-gray-500">
          The narrative LLM may not be available. Check that vLLM is running.
        </p>
        <button
          onClick={() => navigate('/results', { state: location.state })}
          className="mt-4 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
        >
          View Raw Results
        </button>
      </div>
    );
  }

  const confidenceColor = (c: number) =>
    c >= 0.8 ? 'text-green-600' :
    c >= 0.5 ? 'text-amber-600' :
    'text-red-500';

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Executive Summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900">Dossier</h1>
        <div className="mt-1 flex gap-2 text-sm text-gray-500">
          <span className="capitalize">{dossier.subject_type}</span>
          {dossier.date_range && <span>— {dossier.date_range}</span>}
        </div>
        <div className="mt-4 text-gray-700 leading-relaxed">
          {dossier.executive_summary}
        </div>
      </div>

      {/* Patterns */}
      {((dossier.patterns?.length ?? 0) > 0 || (patterns?.length ?? 0) > 0) && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800">Patterns Detected</h2>
          <ul className="mt-3 space-y-2">
            {(dossier.patterns || patterns || []).map((p, i) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="mt-0.5 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                  {p.pattern_type.replace(/_/g, ' ')}
                </span>
                <span className="text-gray-700">{p.description}</span>
                <span className={`ml-auto text-xs ${confidenceColor(p.confidence)}`}>
                  {(p.confidence * 100).toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Per-day sections */}
      {dossier.days?.map((day) => (
        <div key={day.date} className="bg-white rounded-lg shadow overflow-hidden">
          <button
            onClick={() => setExpandedDay(expandedDay === day.date ? null : day.date)}
            className="w-full px-6 py-4 text-left flex justify-between items-center hover:bg-gray-50"
          >
            <div>
              <h3 className="font-semibold text-gray-800">
                {new Date(day.date + 'T00:00:00').toLocaleDateString(undefined, {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </h3>
              <p className="text-sm text-gray-500 mt-0.5">{day.day_summary}</p>
            </div>
            <span className="text-gray-400">
              {expandedDay === day.date ? '▲' : '▼'}
            </span>
          </button>

          {expandedDay === day.date && (
            <div className="px-6 pb-4 space-y-4 border-t border-gray-100">
              {day.entries.map((entry, i) => (
                <div key={i} className="flex gap-4 pt-4">
                  {entry.image_url && (
                    <img
                      src={mediaUrl(entry.image_url)}
                      alt={entry.description}
                      className="w-24 h-24 object-cover rounded-lg flex-shrink-0"
                      loading="lazy"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-sm">
                      {entry.time && <span className="text-gray-500">{entry.time}</span>}
                      {entry.location && (
                        <span className="text-gray-400">{entry.location}</span>
                      )}
                      <span className={`ml-auto text-xs ${confidenceColor(entry.confidence)}`}>
                        {(entry.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-700">{entry.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {/* Export */}
      <div className="flex gap-3 justify-end">
        <button
          onClick={() => {
            const md = formatDossierMarkdown(dossier);
            downloadFile('dossier.md', md, 'text/markdown');
          }}
          className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Download Markdown
        </button>
      </div>
    </div>
  );
}

function formatDossierMarkdown(d: Dossier): string {
  let md = `# Dossier\n\n**Subject**: ${d.subject_type}\n**Period**: ${d.date_range}\n\n`;
  md += `## Executive Summary\n\n${d.executive_summary}\n\n`;

  if (d.patterns?.length) {
    md += `## Patterns\n\n`;
    for (const p of d.patterns) {
      md += `- **${p.pattern_type}**: ${p.description} (${(p.confidence * 100).toFixed(0)}%)\n`;
    }
    md += '\n';
  }

  for (const day of d.days || []) {
    md += `## ${day.date}\n\n${day.day_summary}\n\n`;
    for (const e of day.entries) {
      md += `- **${e.time || 'Unknown time'}** (${e.location || 'Unknown location'}): ${e.description}\n`;
    }
    md += '\n';
  }

  return md;
}

function downloadFile(name: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
