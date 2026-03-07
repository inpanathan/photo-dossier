import type { DetectedFace } from '../api/client';

interface BBoxOverlayProps {
  faces: DetectedFace[];
  imageWidth: number;
  imageHeight: number;
  containerWidth: number;
  containerHeight: number;
  selectedIndex: number | null;
  onSelect: (index: number) => void;
}

export default function BBoxOverlay({
  faces,
  imageWidth,
  imageHeight,
  containerWidth,
  containerHeight,
  selectedIndex,
  onSelect,
}: BBoxOverlayProps) {
  const scaleX = containerWidth / imageWidth;
  const scaleY = containerHeight / imageHeight;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={containerWidth}
      height={containerHeight}
    >
      {faces.map((face, i) => {
        const x = face.bbox.x * scaleX;
        const y = face.bbox.y * scaleY;
        const w = face.bbox.width * scaleX;
        const h = face.bbox.height * scaleY;
        const isSelected = selectedIndex === i;
        const color = face.subject_type === 'human' ? '#3B82F6' : '#10B981';
        const opacity = selectedIndex !== null && !isSelected ? 0.3 : 1;

        return (
          <g key={i} style={{ pointerEvents: 'all', opacity, cursor: 'pointer' }} onClick={() => onSelect(i)}>
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill="none"
              stroke={color}
              strokeWidth={isSelected ? 3 : 2}
            />
            <text
              x={x}
              y={y - 4}
              fill={color}
              fontSize="12"
              fontWeight="bold"
            >
              {face.subject_type} ({(face.confidence * 100).toFixed(0)}%)
            </text>
          </g>
        );
      })}
    </svg>
  );
}
