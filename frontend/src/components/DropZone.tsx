import { useCallback, useState, type DragEvent } from 'react';

interface DropZoneProps {
  onFile: (file: File) => void;
  accept?: string;
}

export default function DropZone({ onFile, accept = 'image/*' }: DropZoneProps) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer ${
        dragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
      }`}
    >
      <input
        type="file"
        accept={accept}
        onChange={handleFileInput}
        className="hidden"
        id="file-input"
      />
      <label htmlFor="file-input" className="cursor-pointer">
        <div className="text-gray-600">
          <p className="text-lg font-medium">Drop a reference photo here</p>
          <p className="mt-1 text-sm text-gray-500">or click to browse</p>
          <p className="mt-2 text-xs text-gray-400">JPEG, PNG, HEIC — max 20MB</p>
        </div>
      </label>
    </div>
  );
}
