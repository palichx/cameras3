import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Settings, Circle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import CameraSettingsDialog from '@/components/CameraSettingsDialog';
import { API_BASE_URL } from '@/config';

const API = `${API_BASE_URL}/api`;

const CameraView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [camera, setCamera] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    fetchCamera();
  }, [id]);

  const fetchCamera = async () => {
    try {
      const response = await axios.get(`${API}/cameras/${id}`);
      setCamera(response.data);
      setLoading(false);
    } catch (error) {
      toast.error('Ошибка загрузки камеры');
      navigate('/');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!camera) {
    return null;
  }

  return (
    <div className="h-screen flex flex-col bg-black">
      {/* Header */}
      <div className="flex items-center justify-between p-4 glass border-b border-[var(--border)]">
        <div className="flex items-center space-x-4">
          <Button
            onClick={() => navigate('/')}
            data-testid="back-button"
            variant="ghost"
            className="text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">{camera.name}</h1>
            <p className="text-sm text-[var(--text-secondary)]">{camera.url}</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Circle
              className={`w-3 h-3 ${
                camera.status === 'active'
                  ? 'text-[var(--success)] fill-[var(--success)]'
                  : 'text-[var(--text-secondary)] fill-[var(--text-secondary)]'
              }`}
            />
            <span className="text-sm text-[var(--text-secondary)]">
              {camera.status === 'active' ? 'Активна' : 'Не активна'}
            </span>
          </div>
          <Button
            onClick={() => setShowSettings(true)}
            data-testid="camera-settings-btn"
            className="bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white"
          >
            <Settings className="w-4 h-4 mr-2" />
            Настройки
          </Button>
        </div>
      </div>

      {/* Live View - Direct MJPEG Stream */}
      <div className="flex-1 flex items-center justify-center p-4" data-testid="live-view-container">
        {camera && camera.status === 'active' ? (
          <img
            src={`${API}/live/${id}`}
            alt="Live feed"
            className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
          />
        ) : (
          <div className="text-center">
            <p className="text-[var(--text-secondary)]">
              {camera?.status === 'active' ? 'Загрузка видео...' : 'Камера не активна'}
            </p>
          </div>
        )}
      </div>

      {/* Camera Settings Dialog */}
      {showSettings && (
        <CameraSettingsDialog
          camera={camera}
          open={showSettings}
          onClose={() => setShowSettings(false)}
          onSave={() => {
            setShowSettings(false);
            fetchCamera();
          }}
        />
      )}
    </div>
  );
};

export default CameraView;
