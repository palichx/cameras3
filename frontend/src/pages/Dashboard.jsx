import { useState, useEffect } from 'react';
import axios from 'axios';
import { Plus, Video, Play, Settings as SettingsIcon, Trash2, Edit } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import CameraSettingsDialog from '@/components/CameraSettingsDialog';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Dashboard = () => {
  const navigate = useNavigate();
  const [cameras, setCameras] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);
  const [newCamera, setNewCamera] = useState({
    name: '',
    url: '',
    username: '',
    password: '',
  });

  useEffect(() => {
    fetchCameras();
    fetchStats();
    const interval = setInterval(() => {
      fetchCameras();
      fetchStats();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchCameras = async () => {
    try {
      const response = await axios.get(`${API}/cameras`);
      setCameras(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching cameras:', error);
      toast.error('Ошибка загрузки камер');
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleAddCamera = async () => {
    if (!newCamera.name || !newCamera.url) {
      toast.error('Заполните обязательные поля');
      return;
    }

    try {
      await axios.post(`${API}/cameras`, newCamera);
      toast.success('Камера добавлена');
      setShowAddDialog(false);
      setNewCamera({ name: '', url: '', username: '', password: '' });
      fetchCameras();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка добавления камеры');
    }
  };

  const handleDeleteCamera = async (id) => {
    if (!window.confirm('Удалить камеру?')) return;

    try {
      await axios.delete(`${API}/cameras/${id}`);
      toast.success('Камера удалена');
      fetchCameras();
    } catch (error) {
      toast.error('Ошибка удаления камеры');
    }
  };

  const handleTestCamera = async (id) => {
    try {
      const response = await axios.post(`${API}/cameras/${id}/test`);
      if (response.data.success) {
        toast.success(response.data.message);
      } else {
        toast.error(response.data.message);
      }
    } catch (error) {
      toast.error('Ошибка тестирования подключения');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-[var(--text-primary)] mb-2">Панель управления</h1>
          <p className="text-[var(--text-secondary)]">Управление системой видеонаблюдения</p>
        </div>
        <Button
          onClick={() => setShowAddDialog(true)}
          disabled={cameras.length >= 20}
          data-testid="add-camera-btn"
          className="bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white px-6 py-3 rounded-xl flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>Добавить камеру</span>
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="glass p-6 rounded-2xl">
          <div className="text-[var(--text-secondary)] text-sm mb-2">Всего камер</div>
          <div className="text-3xl font-bold text-[var(--text-primary)]">{stats.total_cameras || 0}</div>
        </div>
        <div className="glass p-6 rounded-2xl">
          <div className="text-[var(--text-secondary)] text-sm mb-2">Активные</div>
          <div className="text-3xl font-bold text-[var(--success)]">{stats.active_cameras || 0}</div>
        </div>
        <div className="glass p-6 rounded-2xl">
          <div className="text-[var(--text-secondary)] text-sm mb-2">Записей</div>
          <div className="text-3xl font-bold text-[var(--text-primary)]">{stats.total_recordings || 0}</div>
        </div>
        <div className="glass p-6 rounded-2xl">
          <div className="text-[var(--text-secondary)] text-sm mb-2">Использовано</div>
          <div className="text-3xl font-bold text-[var(--text-primary)]">
            {((stats.total_storage_bytes || 0) / 1024 / 1024 / 1024).toFixed(2)} GB
          </div>
        </div>
      </div>

      {/* Cameras Grid */}
      {cameras.length === 0 ? (
        <div className="text-center py-20">
          <Video className="w-16 h-16 text-[var(--text-secondary)] mx-auto mb-4" />
          <p className="text-[var(--text-secondary)] text-lg">Нет добавленных камер</p>
          <Button
            onClick={() => setShowAddDialog(true)}
            className="mt-4 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white"
          >
            Добавить первую камеру
          </Button>
        </div>
      ) : (
        <div className="camera-grid">
          {cameras.map((camera) => (
            <div key={camera.id} className="glass rounded-2xl overflow-hidden group" data-testid={`camera-${camera.id}`}>
              <div
                className="video-container h-48 bg-black cursor-pointer relative"
                onClick={() => navigate(`/camera/${camera.id}`)}
              >
                <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                  <Play className="w-12 h-12 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <img
                  src="/api/placeholder/400/300"
                  alt={camera.name}
                  className="w-full h-full object-cover"
                />
              </div>

              <div className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-lg font-semibold text-[var(--text-primary)]">{camera.name}</h3>
                    <p className="text-sm text-[var(--text-secondary)] truncate">{camera.url}</p>
                  </div>
                  <span
                    className={`status-badge ${
                      camera.status === 'active'
                        ? 'status-active'
                        : camera.status === 'error'
                        ? 'status-error'
                        : 'status-inactive'
                    }`}
                  >
                    {camera.status === 'active' ? 'Активна' : camera.status === 'error' ? 'Ошибка' : 'Не активна'}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <Button
                    onClick={() => navigate(`/camera/${camera.id}`)}
                    data-testid={`view-camera-${camera.id}`}
                    className="flex-1 bg-[var(--bg-tertiary)] hover:bg-[var(--accent)] text-[var(--text-primary)] py-2 rounded-lg"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Просмотр
                  </Button>
                  <Button
                    onClick={() => setEditingCamera(camera)}
                    data-testid={`settings-camera-${camera.id}`}
                    className="bg-[var(--bg-tertiary)] hover:bg-[var(--accent)] text-[var(--text-primary)] p-2 rounded-lg"
                  >
                    <SettingsIcon className="w-4 h-4" />
                  </Button>
                  <Button
                    onClick={() => handleDeleteCamera(camera.id)}
                    data-testid={`delete-camera-${camera.id}`}
                    className="bg-[var(--bg-tertiary)] hover:bg-red-600 text-[var(--text-primary)] p-2 rounded-lg"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Camera Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="bg-[var(--bg-secondary)] border-[var(--border)] text-[var(--text-primary)]">
          <DialogHeader>
            <DialogTitle>Добавить камеру</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Название *</Label>
              <Input
                data-testid="camera-name-input"
                value={newCamera.name}
                onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
                className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]"
                placeholder="Камера 1"
              />
            </div>
            <div>
              <Label>URL *</Label>
              <Input
                data-testid="camera-url-input"
                value={newCamera.url}
                onChange={(e) => setNewCamera({ ...newCamera, url: e.target.value })}
                className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]"
                placeholder="rtsp://..."
              />
            </div>
            <div>
              <Label>Имя пользователя</Label>
              <Input
                data-testid="camera-username-input"
                value={newCamera.username}
                onChange={(e) => setNewCamera({ ...newCamera, username: e.target.value })}
                className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]"
              />
            </div>
            <div>
              <Label>Пароль</Label>
              <Input
                data-testid="camera-password-input"
                type="password"
                value={newCamera.password}
                onChange={(e) => setNewCamera({ ...newCamera, password: e.target.value })}
                className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]"
              />
            </div>
            <Button
              onClick={handleAddCamera}
              data-testid="submit-add-camera"
              className="w-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white"
            >
              Добавить
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Camera Settings Dialog */}
      {editingCamera && (
        <CameraSettingsDialog
          camera={editingCamera}
          open={!!editingCamera}
          onClose={() => setEditingCamera(null)}
          onSave={() => {
            setEditingCamera(null);
            fetchCameras();
          }}
        />
      )}
    </div>
  );
};

export default Dashboard;
