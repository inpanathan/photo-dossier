interface ProgressBarProps {
  progress: number;
  message?: string;
  status?: string;
}

export default function ProgressBar({ progress, message, status }: ProgressBarProps) {
  const pct = Math.round(progress * 100);
  const color =
    status === 'failed' ? 'bg-red-500' :
    status === 'completed' ? 'bg-green-500' :
    'bg-blue-500';

  return (
    <div className="w-full">
      <div className="flex justify-between text-sm text-gray-600 mb-1">
        <span>{message || status || 'Processing...'}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full transition-all duration-300 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
