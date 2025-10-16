import { useState, useEffect } from 'react';
import axios from 'axios';
import { Filter, Play, Trash2, Download, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Recordings = () => {
  const [recordings, setRecordings] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    camera_id: 'all',
    start_date: '',
    end_date: '',
    record_type: 'all',
  });
  const [playingRecording, setPlayingRecording] = useState(null);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  useEffect(() => {
    fetchCameras();
    fetchRecordings();
  }, []);

  useEffect(() => {
    fetchRecordings();
  }, [filters]);

  const fetchCameras = async () => {
    try {
      const response = await axios.get(`${API}/cameras`);
      setCameras(response.data);
    } catch (error) {
      console.error('Error fetching cameras:', error);
    }
  };

  const fetchRecordings = async () => {
    try {
      const params = {};
      if (filters.camera_id) params.camera_id = filters.camera_id;
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;
      if (filters.record_type) params.record_type = filters.record_type;

      const response = await axios.get(`${API}/recordings`, { params });
      setRecordings(response.data);
      setLoading(false);
    } catch (error) {
      toast.error('Ошибка загрузки записей');
      setLoading(false);
    }
  };

  const handleDeleteRecording = async (id) => {
    if (!window.confirm('Удалить запись?')) return;

    try {
      await axios.delete(`${API}/recordings/${id}`);
      toast.success('Запись удалена');
      fetchRecordings();
    } catch (error) {
      toast.error('Ошибка удаления записи');
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const mb = bytes / 1024 / 1024;
    if (mb < 1) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${mb.toFixed(1)} MB`;
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString('ru-RU');
  };

  const handlePlayRecording = (recording) => {
    setPlayingRecording(recording);
    setPlaybackSpeed(1);
  };

  const speedOptions = [1, 2, 4, 6, 8, 10];

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
      <div>
        <h1 className="text-4xl font-bold text-[var(--text-primary)] mb-2">Записи</h1>
        <p className="text-[var(--text-secondary)]">Архив видеозаписей с камер</p>
      </div>

      {/* Filters */}
      <div className="glass p-6 rounded-2xl space-y-4">
        <div className="flex items-center space-x-2 mb-4">
          <Filter className="w-5 h-5 text-[var(--text-secondary)]" />
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">Фильтры</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <Label>Камера</Label>
            <Select value={filters.camera_id || "all"} onValueChange={(value) => setFilters({ ...filters, camera_id: value === "all" ? "" : value })}>
              <SelectTrigger data-testid="filter-camera" className="bg-[var(--bg-tertiary)] border-[var(--border)]">
                <SelectValue placeholder="Все камеры" />
              </SelectTrigger>
              <SelectContent className="bg-[var(--bg-secondary)] border-[var(--border)]">
                <SelectItem value="all">Все камеры</SelectItem>
                {cameras.map((camera) => (
                  <SelectItem key={camera.id} value={camera.id}>
                    {camera.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Тип записи</Label>
            <Select value={filters.record_type || "all"} onValueChange={(value) => setFilters({ ...filters, record_type: value === "all" ? "" : value })}>
              <SelectTrigger data-testid="filter-type" className="bg-[var(--bg-tertiary)] border-[var(--border)]">
                <SelectValue placeholder="Все типы" />
              </SelectTrigger>
              <SelectContent className="bg-[var(--bg-secondary)] border-[var(--border)]">
                <SelectItem value="all">Все типы</SelectItem>
                <SelectItem value="continuous">Непрерывная</SelectItem>
                <SelectItem value="motion">По движению</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Дата начала</Label>
            <Input
              data-testid="filter-start-date"
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
              className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]"
            />
          </div>

          <div>
            <Label>Дата окончания</Label>
            <Input
              data-testid="filter-end-date"
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
              className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]"
            />
          </div>
        </div>
      </div>

      {/* Recordings List */}
      {recordings.length === 0 ? (
        <div className="text-center py-20">
          <Calendar className="w-16 h-16 text-[var(--text-secondary)] mx-auto mb-4" />
          <p className="text-[var(--text-secondary)] text-lg">Нет записей</p>
        </div>
      ) : (
        <div className="space-y-4">
          {recordings.map((recording) => (
            <div
              key={recording.id}
              data-testid={`recording-${recording.id}`}
              className="glass p-6 rounded-2xl flex items-center justify-between hover:bg-[var(--bg-tertiary)] transition-colors"
            >
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <h3 className="text-lg font-semibold text-[var(--text-primary)]">{recording.camera_name}</h3>
                  <span
                    className={`status-badge ${
                      recording.record_type === 'motion' ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'
                    }`}
                  >
                    {recording.record_type === 'motion' ? 'По движению' : 'Непрерывная'}
                  </span>
                </div>
                <div className="flex items-center space-x-6 text-sm text-[var(--text-secondary)]">
                  <span>📅 {formatDate(recording.start_time)}</span>
                  <span>⏱️ {formatDuration(recording.duration_seconds)}</span>
                  <span>💾 {formatFileSize(recording.file_size)}</span>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  onClick={() => handlePlayRecording(recording)}
                  data-testid={`play-recording-${recording.id}`}
                  className="bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Воспроизвести
                </Button>
                <Button
                  onClick={() => handleDeleteRecording(recording.id)}
                  data-testid={`delete-recording-${recording.id}`}
                  variant="outline"
                  className="border-[var(--border)] text-[var(--text-secondary)] hover:bg-red-600 hover:text-white"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Video Player Dialog */}
      {playingRecording && (
        <Dialog open={!!playingRecording} onOpenChange={() => setPlayingRecording(null)}>
          <DialogContent className="max-w-5xl bg-[var(--bg-secondary)] border-[var(--border)] text-[var(--text-primary)]">
            <DialogHeader>
              <DialogTitle>{playingRecording.camera_name} - {formatDate(playingRecording.start_time)}</DialogTitle>
            </DialogHeader>

            <div className="space-y-4">
              <video
                data-testid="video-player"
                key={playingRecording.id}
                controls
                autoPlay
                className="w-full rounded-lg bg-black"
                src={`${API}/recordings/${playingRecording.id}/video`}
                onRateChange={(e) => setPlaybackSpeed(e.target.playbackRate)}
              >
                Ваш браузер не поддерживает воспроизведение видео.
              </video>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label>Скорость воспроизведения: {playbackSpeed}x</Label>
                </div>
                <div className="flex items-center space-x-2">
                  {speedOptions.map((speed) => (
                    <Button
                      key={speed}
                      data-testid={`speed-${speed}x`}
                      onClick={() => {
                        const video = document.querySelector('video');
                        if (video) {
                          video.playbackRate = speed;
                          setPlaybackSpeed(speed);
                        }
                      }}
                      className={`${
                        playbackSpeed === speed
                          ? 'bg-[var(--accent)] text-white'
                          : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
                      } hover:bg-[var(--accent)]`}
                    >
                      {speed}x
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default Recordings;
