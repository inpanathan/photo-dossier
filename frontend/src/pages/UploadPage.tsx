import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { detect, query, runPipeline, type DetectedFace, type DetectionResult } from '../api/client';
import BBoxOverlay from '../components/BBoxOverlay';
import DropZone from '../components/DropZone';
import ProgressBar from '../components/ProgressBar';
import { useJobPoller } from '../hooks/useJobPoller';

export default function UploadPage() {
  const navigate = useNavigate();
  const imgRef = useRef<HTMLImageElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [detection, setDetection] = useState<DetectionResult | null>(null);
  const [selectedFace, setSelectedFace] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [imgDims, setImgDims] = useState({ w: 0, h: 0 });

  const { job } = useJobPoller(jobId);

  const handleFile = useCallback(async (f: File) => {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setDetection(null);
    setSelectedFace(null);
    setError(null);
    setJobId(null);

    setLoading(true);
    try {
      const result = await detect(f);
      setDetection(result);
      if (result.faces.length === 1) setSelectedFace(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Detection failed');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSearch = useCallback(async () => {
    if (!file || !detection || selectedFace === null) return;
    const face = detection.faces[selectedFace];

    setLoading(true);
    setError(null);
    try {
      const resp = await runPipeline(file, face.subject_type, face.bbox);
      setJobId(resp.job_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pipeline failed');
    } finally {
      setLoading(false);
    }
  }, [file, detection, selectedFace]);

  const handleImgLoad = useCallback(() => {
    if (imgRef.current) {
      setImgDims({ w: imgRef.current.clientWidth, h: imgRef.current.clientHeight });
    }
  }, []);

  // Navigate to results when job completes
  if (job?.status === 'completed' && job.result) {
    const state = { result: job.result, jobId: job.id };
    navigate('/results', { state });
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Reference Photo</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload a photo containing the person or pet you want to find.
        </p>
      </div>

      {!preview && <DropZone onFile={handleFile} />}

      {preview && (
        <div className="space-y-4">
          <div className="relative inline-block">
            <img
              ref={imgRef}
              src={preview}
              alt="Preview"
              className="max-w-full rounded-lg shadow"
              onLoad={handleImgLoad}
            />
            {detection && imgDims.w > 0 && (
              <BBoxOverlay
                faces={detection.faces}
                imageWidth={detection.image_width}
                imageHeight={detection.image_height}
                containerWidth={imgDims.w}
                containerHeight={imgDims.h}
                selectedIndex={selectedFace}
                onSelect={setSelectedFace}
              />
            )}
          </div>

          {detection && detection.faces.length === 0 && (
            <p className="text-amber-600 text-sm">
              No faces detected. Try a clearer photo.
            </p>
          )}

          {detection && detection.faces.length > 1 && selectedFace === null && (
            <p className="text-blue-600 text-sm">
              Click a bounding box to select the subject to search for.
            </p>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => {
                setFile(null);
                setPreview(null);
                setDetection(null);
                setSelectedFace(null);
                setJobId(null);
              }}
              className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Clear
            </button>

            <button
              onClick={handleSearch}
              disabled={selectedFace === null || loading || !!jobId}
              className="px-6 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Processing...' : 'Search Corpus'}
            </button>
          </div>
        </div>
      )}

      {jobId && job && (
        <div className="mt-4">
          <ProgressBar
            progress={job.progress}
            message={job.message}
            status={job.status}
          />
          {job.status === 'failed' && (
            <p className="mt-2 text-red-600 text-sm">{job.error}</p>
          )}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && !jobId && (
        <div className="text-center text-gray-500 text-sm">Detecting faces...</div>
      )}
    </div>
  );
}
