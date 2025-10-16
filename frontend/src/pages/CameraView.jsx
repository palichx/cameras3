import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Settings, Circle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import CameraSettingsDialog from '@/components/CameraSettingsDialog';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CameraView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [camera, setCamera] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [liveFrame, setLiveFrame] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    fetchCamera();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
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

  const connectWebSocket = () => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/live/${id}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.frame) {
          setLiveFrame(data.frame);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      // Attempt to reconnect after 2 seconds
      setTimeout(() => {
        if (wsRef.current === ws) {
          connectWebSocket();
        }
      }, 2000);
    };
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

      {/* Live View */}
      <div className="flex-1 flex items-center justify-center p-4" data-testid="live-view-container">
        {liveFrame ? (
          <img
            src={`data:image/jpeg;base64,${liveFrame}`}
            alt="Live feed"
            className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
          />
        ) : (
          <div className="text-center">
            <div className="spinner mx-auto mb-4"></div>
            <p className="text-[var(--text-secondary)]">Загрузка видео...</p>
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
