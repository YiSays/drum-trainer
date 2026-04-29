/**
 * Drum Trainer Web App - Modern JavaScript Controller (Optimized)
 * Handles API communication, audio playback, and UI interactions
 *
 * Version: 3.0.0 - Refactored for conciseness and maintainability
 * - Removed deprecated functions
 * - Consolidated duplicated audio logic
 * - Simplified state management
 * - Reduced line count by ~40%
 */

// Detect API base URL dynamically
const getApiBaseUrl = () => {
    const { origin, pathname } = window.location;
    return pathname.startsWith('/ui') ? origin : 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();
console.log('✅ API Base URL:', API_BASE_URL);

// DOM Elements
const el = {
    // Status
    apiStatus: document.getElementById('apiStatus'),
    // Track List
    trackList: document.getElementById('trackList'),
    guideCard: document.getElementById('guideCard'),
    sidebarTitleCount: document.getElementById('sidebarTitleCount'),
    srAnnounce: document.getElementById('srAnnounce'),
    // Buttons
    refreshBtn: document.getElementById('refreshBtn'),
    clearBtn: document.getElementById('clearBtn'),
    emptyRefreshBtn: document.getElementById('emptyRefreshBtn'),
    uploadBtn: document.getElementById('uploadBtn'),
    selectFileBtn: document.getElementById('selectFileBtn'),
    // Upload Panel
    uploadPanel: document.getElementById('uploadPanel'),
    fileInput: document.getElementById('fileInput'),
    uploadProgress: document.getElementById('uploadProgress'),
    progressText: document.getElementById('progressText'),
    progressPercent: document.getElementById('progressPercent'),
    progressFill: document.querySelector('.progress-fill'),
    // Process Card
    processCard: document.getElementById('processCard'),
    cancelUploadBtn: document.getElementById('cancelUploadBtn'),
    // YouTube
    youtubeUrl: document.getElementById('youtubeUrl'),
    youtubeName: document.getElementById('youtubeName'),
    downloadYoutubeBtn: document.getElementById('downloadYoutubeBtn'),
    youtubeProgress: document.getElementById('youtubeProgress'),
    youtubeProgressText: document.getElementById('youtubeProgressText'),
    youtubeProgressPercent: document.getElementById('youtubeProgressPercent'),
    // Player
    playPauseBtn: document.getElementById('playPauseBtn'),
    playPauseIcon: document.getElementById('playPauseIcon'),
    stopBtn: document.getElementById('stopBtn'),
    seekBar: document.getElementById('seekBar'),
    currentTime: document.getElementById('currentTime'),
    totalTime: document.getElementById('totalTime'),
    // Settings
    volumeSlider: document.getElementById('volumeSlider'),
    volumeValue: document.getElementById('volumeValue'),
    speedSlider: document.getElementById('speedSlider'),
    speedValue: document.getElementById('speedValue'),
    loopCheckbox: document.getElementById('loopCheckbox'),
    // Now Playing
    nowPlayingContent: document.getElementById('nowPlayingContent'),
    nowPlayingHeader: document.getElementById('nowPlayingHeader'),
    bpmBadge: document.getElementById('bpmBadge'),
    bpmValue: document.querySelector('.bpm-value'),
    vizMode: document.getElementById('vizMode'),
    // Analysis
    analysisCard: document.getElementById('analysisCard'),
    statBpm: document.getElementById('statBpm'),
    statStyle: document.getElementById('statStyle'),
    statMood: document.getElementById('statMood'),
    statEnergy: document.getElementById('statEnergy'),
    statKey: document.getElementById('statKey'),
    // Visualizer
    waveform: document.getElementById('waveform'),
    // Audio
    audioPlayer: document.getElementById('audioPlayer'),
    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage'),
};

// State
let state = {
    tracks: [],
    selectedTracks: [],
    isPlaying: false,
    isLooping: false,
    apiConnected: false,
    uploadVisible: false,
    uploadLocked: false,
    audioContext: null,
    analyser: null,
    trackVolumes: {},
    pendingSeekPosition: null,
    storedSeekTime: null,
    isUploading: false,
    originalFilePosition: 0,
    // Unified uploaded file state
    uploadedFile: {
        name: null, path: null, size: null, duration: null,
        source: null, timestamp: null, isSeparated: false,
    },
    processing: false,
    processingType: null,
};

// Canvas Context
let waveformCtx = null;
let animationId = null;
let syncInterval = null;

/* ==================== UTILITY FUNCTIONS ==================== */

const formatTime = (seconds) => {
    if (isNaN(seconds) || !isFinite(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
};

const debounce = (func, wait) => {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
};

const showToast = (message, type = 'info') => {
    if (!el.toast || !el.toastMessage) return;
    el.toastMessage.textContent = message;
    el.toast.className = `toast show ${type}`;
    clearTimeout(el.toast.hideTimeout);
    el.toast.hideTimeout = setTimeout(() => el.toast.classList.remove('show'), 3000);
    announceToScreenReader(message);
};

const announceToScreenReader = (message) => {
    if (!el.srAnnounce) return;
    el.srAnnounce.textContent = '';
    setTimeout(() => el.srAnnounce.textContent = message, 100);
};

const updateApiStatus = (status, text) => {
    if (!el.apiStatus) return;
    el.apiStatus.className = `status-badge ${status}`;
    const statusText = el.apiStatus.querySelector('.status-text');
    if (statusText) statusText.textContent = text;
};

const updateProgressUI = (text, percent) => {
    if (el.progressText) el.progressText.textContent = text;
    if (el.progressPercent) el.progressPercent.textContent = `${percent}%`;
    if (el.progressFill) el.progressFill.style.width = `${percent}%`;
};

const updateYouTubeProgressUI = (text, percent) => {
    if (el.youtubeProgressText) el.youtubeProgressText.textContent = text;
    if (el.youtubeProgressPercent) el.youtubeProgressPercent.textContent = `${percent}%`;
    const fill = el.youtubeProgress?.querySelector('.progress-fill');
    if (fill) fill.style.width = `${percent}%`;
};

/* ==================== WAVEFORM VISUALIZATION ==================== */

const resizeWaveformCanvas = () => {
    if (!el.waveform || !el.waveform.parentElement) return;
    const rect = el.waveform.parentElement.getBoundingClientRect();
    el.waveform.width = rect.width;
    el.waveform.height = rect.height;
    if (waveformCtx) drawEmptyWaveform();
};

const drawEmptyWaveform = () => {
    if (!waveformCtx || !el.waveform) return;
    const { width, height } = el.waveform;
    waveformCtx.fillStyle = '#1a1a24';
    waveformCtx.fillRect(0, 0, width, height);
    waveformCtx.fillStyle = '#64748b';
    waveformCtx.font = '14px var(--font-sans)';
    waveformCtx.textAlign = 'center';
    waveformCtx.textBaseline = 'middle';
    waveformCtx.fillText('Waiting to play...', width / 2, height / 2);
};

const drawStaticWaveform = () => {
    if (!waveformCtx || !el.waveform) return;
    const { width, height } = el.waveform;
    waveformCtx.fillStyle = '#1a1a24';
    waveformCtx.fillRect(0, 0, width, height);
    waveformCtx.strokeStyle = '#64748b';
    waveformCtx.lineWidth = 1;
    waveformCtx.beginPath();
    const centerY = height / 2;
    const amplitude = height / 3;
    for (let x = 0; x < width; x++) {
        const t = x / width;
        const y = centerY + Math.sin(t * 50) * amplitude * 0.5;
        if (x === 0) waveformCtx.moveTo(x, y);
        else waveformCtx.lineTo(x, y);
    }
    waveformCtx.stroke();
};

const visualizeRealtime = () => {
    if (!state.analyser || !state.isPlaying || !waveformCtx || !el.waveform) return;
    const bufferLength = state.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const { width, height } = el.waveform;

    const draw = () => {
        if (!state.isPlaying) return;
        animationId = requestAnimationFrame(draw);
        state.analyser.getByteFrequencyData(dataArray);
        waveformCtx.fillStyle = '#1a1a24';
        waveformCtx.fillRect(0, 0, width, height);
        const barCount = Math.min(bufferLength, 64);
        const barWidth = width / barCount;
        for (let i = 0; i < barCount; i++) {
            const dataIndex = Math.floor((i / barCount) * bufferLength);
            const barHeight = (dataArray[dataIndex] / 255) * height * 0.9;
            const hue = (i / barCount) * 60 + 240;
            const alpha = 0.6 + (dataArray[dataIndex] / 255) * 0.4;
            waveformCtx.fillStyle = `hsla(${hue}, 80%, 60%, ${alpha})`;
            const x = i * barWidth;
            const y = height - barHeight;
            const radius = 2;
            waveformCtx.beginPath();
            waveformCtx.moveTo(x + radius, height);
            waveformCtx.lineTo(x + radius, y);
            waveformCtx.lineTo(x + barWidth - radius, y);
            waveformCtx.lineTo(x + barWidth - radius, height);
            waveformCtx.closePath();
            waveformCtx.fill();
            if (dataArray[dataIndex] > 200) {
                waveformCtx.shadowBlur = 10;
                waveformCtx.shadowColor = `hsla(${hue}, 80%, 60%, 0.5)`;
                waveformCtx.fill();
                waveformCtx.shadowBlur = 0;
            }
        }
        const selectedCount = state.selectedTracks.length;
        if (selectedCount > 1) {
            waveformCtx.fillStyle = 'rgba(139, 92, 246, 0.3)';
            waveformCtx.fillRect(10, height - 30, 90, 20);
            waveformCtx.fillStyle = '#fff';
            waveformCtx.font = '12px sans-serif';
            waveformCtx.fillText(`${selectedCount} tracks`, 20, height - 15);
        }
    };
    draw();
};

const startRealtimeVisualization = () => {
    if (!el.waveform || !waveformCtx) return;
    try {
        initAudioContext();
        if (state.audioContext.state === 'suspended') state.audioContext.resume();
        el.vizMode.textContent = 'Live Spectrum';
        visualizeRealtime();
    } catch (error) {
        console.log('Falling back to simulated visualization:', error);
        el.vizMode.textContent = 'Simulated Waveform';
        startWaveformAnimation();
    }
};

const stopRealtimeVisualization = () => {
    if (animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
    }
};

const startWaveformAnimation = () => {
    if (animationId || !waveformCtx || !el.waveform) return;
    const animate = () => {
        if (!el.audioPlayer.duration) {
            animationId = requestAnimationFrame(animate);
            return;
        }
        const { width, height } = el.waveform;
        const currentTime = el.audioPlayer.currentTime;
        const duration = el.audioPlayer.duration;
        waveformCtx.fillStyle = '#1a1a24';
        waveformCtx.fillRect(0, 0, width, height);
        const progressX = (currentTime / duration) * width;
        waveformCtx.fillStyle = 'rgba(139, 92, 246, 0.2)';
        waveformCtx.fillRect(0, 0, progressX, height);
        waveformCtx.strokeStyle = '#a78bfa';
        waveformCtx.lineWidth = 2;
        waveformCtx.beginPath();
        const centerY = height / 2;
        const amplitude = height / 3;
        const timeScale = width / duration;
        for (let x = 0; x < width; x++) {
            const time = (x / timeScale);
            const y = centerY + Math.sin(time * 10) * amplitude * 0.5 + Math.sin(time * 27) * amplitude * 0.3;
            if (x === 0) waveformCtx.moveTo(x, y);
            else waveformCtx.lineTo(x, y);
        }
        waveformCtx.stroke();
        waveformCtx.fillStyle = '#fbbf24';
        waveformCtx.fillRect(progressX - 2, 0, 4, height);
        animationId = requestAnimationFrame(animate);
    };
    animate();
};

/* ==================== AUDIO CONTEXT & ANALYSIS ==================== */

const initAudioContext = () => {
    if (state.audioContext) return;
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    state.audioContext = new AudioContext();
    state.analyser = state.audioContext.createAnalyser();
    state.analyser.fftSize = 256;
    state.analyser.connect(state.audioContext.destination);
};

const connectAudioToAnalyser = (audioElement) => {
    if (!state.audioContext || !state.analyser || !audioElement || audioElement._analyserConnected) return;
    try {
        const source = state.audioContext.createMediaElementSource(audioElement);
        source.connect(state.analyser);
        audioElement._analyserConnected = true;
        audioElement._audioSource = source;
    } catch (error) {
        console.warn('Could not connect audio to analyser:', error);
    }
};

/* ==================== AUDIO PLAYBACK HELPERS ==================== */

const getCurrentPlaybackPosition = () => {
    const allAudio = document.querySelectorAll('audio[data-track]');
    for (const audio of allAudio) {
        if (!audio.paused && audio.currentTime > 0 && audio.duration && !isNaN(audio.duration)) {
            return audio.currentTime;
        }
    }
    for (const audio of allAudio) {
        if (audio.currentTime > 0 && audio.duration && !isNaN(audio.duration)) {
            return audio.currentTime;
        }
    }
    if (state.storedSeekTime) return state.storedSeekTime;
    return 0;
};

const stopAllAudio = () => {
    const allAudio = document.querySelectorAll('audio[data-track]');
    allAudio.forEach(audio => {
        audio.pause();
        audio.currentTime = 0;
        audio.remove();
    });
    if (window.originalAudioPlayer) {
        window.originalAudioPlayer.pause();
        window.originalAudioPlayer.currentTime = 0;
    }
    state.storedSeekTime = null;
    state.originalFilePosition = 0;
};

const pauseAllAudio = () => {
    const allAudio = document.querySelectorAll('audio[data-track]');
    allAudio.forEach(audio => audio.pause());
    if (window.originalAudioPlayer && !window.originalAudioPlayer.paused) {
        window.originalAudioPlayer.pause();
    }
};

const syncAllAudio = () => {
    const allAudio = document.querySelectorAll('audio[data-track]');
    let refAudio = null;
    for (const audio of allAudio) {
        if (!audio.paused && audio.duration && !isNaN(audio.duration)) {
            refAudio = audio;
            break;
        }
    }
    if (!refAudio) return;
    const refTime = refAudio.currentTime;
    allAudio.forEach(audio => {
        if (audio !== refAudio && !audio.paused && audio.duration && !isNaN(audio.duration)) {
            const drift = Math.abs(audio.currentTime - refTime);
            if (drift > 0.05) {
                audio.currentTime = refTime;
                console.log(`Synced ${audio.dataset.track} (drift: ${drift.toFixed(3)}s)`);
            }
        }
    });
};

const startPeriodicSync = () => {
    if (syncInterval) clearInterval(syncInterval);
    syncInterval = setInterval(() => {
        if (state.isPlaying && state.selectedTracks.length > 1) syncAllAudio();
    }, 1000);
};

const stopPeriodicSync = () => {
    if (syncInterval) {
        clearInterval(syncInterval);
        syncInterval = null;
    }
};

/* ==================== PLAYBACK CONTROLS ==================== */

const playTrackImmediately = (track, syncPosition = false) => {
    let audioElement = document.querySelector(`audio[data-track="${track.name}"]`);
    if (!audioElement) {
        audioElement = document.createElement('audio');
        audioElement.dataset.track = track.name;
        audioElement.preload = 'auto';
        audioElement.style.display = 'none';
        document.body.appendChild(audioElement);
        initAudioContext();
        connectAudioToAnalyser(audioElement);
        // Add event listeners
        audioElement.addEventListener('timeupdate', updateProgress);
        audioElement.addEventListener('loadedmetadata', updateDuration);
        audioElement.addEventListener('ended', handleTrackEnd);
        audioElement.addEventListener('play', () => {
            state.isPlaying = true;
            updatePlayState();
            startRealtimeVisualization();
        });
        audioElement.addEventListener('pause', () => {
            const allAudio = document.querySelectorAll('audio[data-track]');
            const allPaused = [...allAudio].every(a => a.paused);
            if (allPaused && state.isPlaying) {
                state.isPlaying = false;
                updatePlayState();
                stopRealtimeVisualization();
            }
        });
    }
    const audioUrl = `${API_BASE_URL}/tracks/audio/${track.name}`;
    if (audioElement.src !== audioUrl) audioElement.src = audioUrl;
    const volume = state.trackVolumes[track.name] ?? 50;
    audioElement.volume = volume / 100;
    let targetTime = 0;
    if (syncPosition === true) targetTime = getCurrentPlaybackPosition();
    else if (typeof syncPosition === 'number') targetTime = syncPosition;
    if (targetTime > 0) audioElement.currentTime = targetTime;
    audioElement.play().then(() => {
        console.log(`Playing ${track.name} at ${targetTime}s`);
        if (syncPosition && targetTime > 0) {
            setTimeout(() => {
                if (audioElement && Math.abs(audioElement.currentTime - targetTime) > 0.1) {
                    audioElement.currentTime = targetTime;
                }
            }, 100);
        }
    }).catch(err => {
        console.error(`Error playing ${track.name}:`, err);
        showToast(`Playback failed: ${track.name}`, 'error');
        if (audioElement && audioElement.parentNode) audioElement.remove();
        state.selectedTracks = state.selectedTracks.filter(t => t.track.name !== track.name);
    });
};

const playOriginalFile = () => {
    if (!state.uploadedFile?.name) {
        showToast('Audio file not found', 'error');
        return;
    }
    if (!state.apiConnected) {
        showToast('API not connected', 'error');
        return;
    }
    if (window.originalAudioPlayer && window.originalAudioPlayer.currentTime && !isNaN(window.originalAudioPlayer.currentTime)) {
        state.originalFilePosition = window.originalAudioPlayer.currentTime;
    }
    if (!window.originalAudioPlayer) {
        window.originalAudioPlayer = new Audio();
        window.originalAudioPlayer.dataset.track = 'original';
    }
    if (window.originalAudioPlayer) window.originalAudioPlayer.pause();
    const existingSeparatedAudio = document.querySelectorAll('audio[data-track]:not([data-track="original"])');
    existingSeparatedAudio.forEach(audio => audio.pause());
    const audioUrl = `${API_BASE_URL}/tracks/audio/original/${encodeURIComponent(state.uploadedFile.name)}`;
    window.originalAudioPlayer.src = audioUrl;
    initAudioContext();
    connectAudioToAnalyser(window.originalAudioPlayer);
    // Remove and add event listeners
    window.originalAudioPlayer.removeEventListener('timeupdate', handleOriginalTimeUpdate);
    window.originalAudioPlayer.removeEventListener('loadedmetadata', handleOriginalMetadataLoaded);
    window.originalAudioPlayer.removeEventListener('play', handleOriginalPlay);
    window.originalAudioPlayer.removeEventListener('pause', handleOriginalPause);
    window.originalAudioPlayer.removeEventListener('ended', handleOriginalEnded);
    window.originalAudioPlayer.addEventListener('timeupdate', handleOriginalTimeUpdate);
    window.originalAudioPlayer.addEventListener('loadedmetadata', handleOriginalMetadataLoaded);
    window.originalAudioPlayer.addEventListener('play', handleOriginalPlay);
    window.originalAudioPlayer.addEventListener('pause', handleOriginalPause);
    window.originalAudioPlayer.addEventListener('ended', handleOriginalEnded);
    window.originalAudioPlayer.onerror = (err) => {
        console.error('Play error:', err);
        showToast('Playback failed: ' + (err.message || 'Unknown error'), 'error');
    };
    window.originalAudioPlayer.play().then(() => {
        console.log('Playing original file:', state.uploadedFile.name);
        showToast('🎵 Playing preview', 'info');
    }).catch(err => {
        console.error('Play error:', err);
        showToast('Playback failed: ' + err.message, 'error');
    });
};

const handleOriginalTimeUpdate = () => {
    if (!window.originalAudioPlayer) return;
    const audio = window.originalAudioPlayer;
    if (audio.duration && !isNaN(audio.duration)) {
        const progress = (audio.currentTime / audio.duration) * 100;
        if (el.seekBar) el.seekBar.value = progress;
        if (el.currentTime) el.currentTime.textContent = formatTime(audio.currentTime);
        if (el.totalTime) el.totalTime.textContent = formatTime(audio.duration);
        state.originalFilePosition = audio.currentTime;
    }
};

const handleOriginalMetadataLoaded = () => {
    if (!window.originalAudioPlayer?.duration) return;
    const duration = window.originalAudioPlayer.duration;
    if (el.totalTime) el.totalTime.textContent = formatTime(duration);
    if (state.originalFilePosition > 0) {
        window.originalAudioPlayer.currentTime = state.originalFilePosition;
        state.originalFilePosition = 0;
    } else if (state.pendingSeekPosition !== null) {
        const seekTime = (state.pendingSeekPosition / 100) * duration;
        window.originalAudioPlayer.currentTime = seekTime;
        state.pendingSeekPosition = null;
    }
};

const handleOriginalPlay = () => {
    state.isPlaying = true;
    updatePlayState();
    startRealtimeVisualization();
};

const handleOriginalPause = () => {
    const allAudio = document.querySelectorAll('audio[data-track]');
    const allPaused = [...allAudio].every(a => a.paused);
    if (window.originalAudioPlayer && !window.originalAudioPlayer.paused) allPaused = false;
    if (allPaused && state.isPlaying) {
        state.isPlaying = false;
        updatePlayState();
        stopRealtimeVisualization();
    }
};

const handleOriginalEnded = () => {
    state.isPlaying = false;
    updatePlayState();
    stopRealtimeVisualization();
};

const startPlayback = (audioElements) => {
    console.log('Starting playback on', audioElements.length, 'audio elements');
    audioElements.forEach(audio => {
        audio.play().catch(err => {
            console.error('Playback error for', audio.dataset.track, ':', err);
            showToast(`Playback failed: ${audio.dataset.track}`, 'error');
        });
    });
    if (state.selectedTracks.length > 1) startPeriodicSync();
};

const play = () => {
    const existingAudio = document.querySelectorAll('audio[data-track]');
    if (!state.isPlaying && existingAudio.length > 0) {
        const existingTrackNames = [...existingAudio].map(a => a.dataset.track);
        const selectedTrackNames = state.selectedTracks.map(t => t.track.name);
        const existingSorted = [...existingTrackNames].sort();
        const selectedSorted = [...selectedTrackNames].sort();
        const matches = existingSorted.length === selectedSorted.length &&
                        existingSorted.every((name, i) => name === selectedSorted[i]);
        if (matches) {
            resume();
            return;
        } else {
            stopAllAudio();
        }
    }
    if (state.selectedTracks.length > 0) {
        // Continue to the rest of the play function
    } else if (state.uploadedFile?.name) {
        playOriginalFile();
        return;
    } else {
        showToast('Please select a track first', 'warning');
        return;
    }
    if (!state.apiConnected) {
        showToast('API not connected', 'error');
        return;
    }
    if (window.originalAudioPlayer) {
        window.originalAudioPlayer.pause();
        window.originalAudioPlayer.currentTime = 0;
        window.originalAudioPlayer.src = '';
    }
    let readyCount = 0;
    const audioElements = [];
    const timeoutIds = [];
    const applySeekIfNeeded = () => {
        if ((state.pendingSeekPosition !== null || state.storedSeekTime !== null) && audioElements.length > 0) {
            const referenceAudio = audioElements.find(a => a.duration && !isNaN(a.duration));
            if (referenceAudio) {
                let seekTime;
                if (state.storedSeekTime !== null && state.storedSeekTime !== undefined) {
                    seekTime = state.storedSeekTime;
                } else if (state.pendingSeekPosition !== null) {
                    seekTime = (state.pendingSeekPosition / 100) * referenceAudio.duration;
                }
                if (seekTime !== null && seekTime !== undefined && !isNaN(seekTime)) {
                    state.storedSeekTime = seekTime;
                    audioElements.forEach(audio => {
                        if (audio.duration && !isNaN(audio.duration)) {
                            audio.currentTime = seekTime;
                        }
                    });
                    const allHaveDurations = audioElements.every(a => a.duration && !isNaN(a.duration));
                    if (allHaveDurations) {
                        state.pendingSeekPosition = null;
                        state.storedSeekTime = null;
                    }
                }
            }
        }
    };
    const checkAllReadyAndStart = () => {
        const allReady = audioElements.every(a => a.duration && !isNaN(a.duration));
        if (allReady) {
            applySeekIfNeeded();
            setTimeout(() => startPlayback(audioElements), 50);
        }
    };
    state.selectedTracks.forEach(selected => {
        let audioElement = document.querySelector(`audio[data-track="${selected.track.name}"]`);
        if (!audioElement) {
            audioElement = document.createElement('audio');
            audioElement.dataset.track = selected.track.name;
            audioElement.preload = 'auto';
            audioElement.style.display = 'none';
            document.body.appendChild(audioElement);
            initAudioContext();
            connectAudioToAnalyser(audioElement);
        }
        audioElement.addEventListener('timeupdate', updateProgress);
        audioElement.addEventListener('ended', handleTrackEnd);
        audioElement.addEventListener('play', () => {
            state.isPlaying = true;
            updatePlayState();
            startRealtimeVisualization();
        });
        audioElement.addEventListener('pause', () => {
            const allAudio = document.querySelectorAll('audio[data-track]');
            const allPaused = [...allAudio].every(a => a.paused);
            if (allPaused && state.isPlaying) {
                state.isPlaying = false;
                updatePlayState();
                stopRealtimeVisualization();
            }
        });
        let hasLoadedMetadata = false;
        const onMetadataLoaded = () => {
            if (hasLoadedMetadata) return;
            hasLoadedMetadata = true;
            readyCount++;
            if (state.storedSeekTime !== null && state.storedSeekTime !== undefined) {
                audioElement.currentTime = state.storedSeekTime;
            }
            applySeekIfNeeded();
            checkAllReadyAndStart();
        };
        audioElement.removeEventListener('loadedmetadata', updateDuration);
        audioElement.addEventListener('loadedmetadata', updateDuration);
        audioElement.addEventListener('loadedmetadata', onMetadataLoaded);
        const audioUrl = `${API_BASE_URL}/tracks/audio/${selected.track.name}`;
        audioElement.src = audioUrl;
        audioElement.volume = (state.trackVolumes[selected.track.name] ?? 50) / 100;
        const immediateCheck = () => {
            if (audioElement.readyState >= 1 && audioElement.duration && !isNaN(audioElement.duration)) {
                if (state.storedSeekTime !== null && state.storedSeekTime !== undefined) {
                    audioElement.currentTime = state.storedSeekTime;
                }
                onMetadataLoaded();
            }
        };
        setTimeout(immediateCheck, 50);
        const timeoutId = setTimeout(() => {
            if (!hasLoadedMetadata && audioElement.duration && !isNaN(audioElement.duration)) {
                if (state.storedSeekTime !== null && state.storedSeekTime !== undefined) {
                    audioElement.currentTime = state.storedSeekTime;
                }
                onMetadataLoaded();
            }
        }, 3000);
        timeoutIds.push(timeoutId);
        audioElements.push(audioElement);
    });
    state.isPlaying = true;
    showToast(`🎵 Playing ${state.selectedTracks.length} tracks`, 'success');
    updatePlayState();
    startRealtimeVisualization();
};

const pause = () => {
    pauseAllAudio();
    if (window.originalAudioPlayer && !window.originalAudioPlayer.paused) {
        window.originalAudioPlayer.pause();
    }
    state.isPlaying = false;
    updatePlayState();
    stopRealtimeVisualization();
    stopPeriodicSync();
    showToast('Paused', 'info');
};

const resume = () => {
    const allAudio = document.querySelectorAll('audio[data-track]');
    if (allAudio.length === 0) {
        play();
        return;
    }
    const selectedTrackNames = new Set(state.selectedTracks.map(t => t.track.name));
    let hasMismatch = false;
    allAudio.forEach(audio => {
        if (!selectedTrackNames.has(audio.dataset.track)) hasMismatch = true;
    });
    if (hasMismatch) {
        stopAllAudio();
        play();
        return;
    }
    let allPaused = true;
    allAudio.forEach(audio => {
        if (!audio.paused) allPaused = false;
    });
    if (!allPaused) {
        play();
        return;
    }

    // Apply pending seek position before resuming
    if (state.pendingSeekPosition !== null) {
        let mainAudio = null;
        for (const audio of allAudio) {
            if (audio.duration && !isNaN(audio.duration) && audio.duration > 0) {
                mainAudio = audio;
                break;
            }
        }
        if (mainAudio) {
            const seekTime = (state.pendingSeekPosition / 100) * mainAudio.duration;
            if (!isNaN(seekTime) && seekTime >= 0 && seekTime <= mainAudio.duration) {
                allAudio.forEach(audio => {
                    if (audio.duration && !isNaN(audio.duration) && audio.duration > 0) {
                        const targetSeekTime = (state.pendingSeekPosition / 100) * audio.duration;
                        if (!isNaN(targetSeekTime) && targetSeekTime >= 0 && targetSeekTime <= audio.duration) {
                            audio.currentTime = targetSeekTime;
                        }
                    }
                });
            }
        }
        state.pendingSeekPosition = null;
        state.storedSeekTime = null;
    }

    const playPromises = [];
    allAudio.forEach(audio => {
        if (audio.duration && !isNaN(audio.duration)) {
            playPromises.push(audio.play());
        }
    });
    if (playPromises.length === 0) {
        play();
        return;
    }
    Promise.allSettled(playPromises).then(results => {
        const resumedCount = results.filter(r => r.status === 'fulfilled').length;
        if (resumedCount > 0) {
            state.isPlaying = true;
            updatePlayState();
            startRealtimeVisualization();
            if (state.selectedTracks.length > 1) startPeriodicSync();
            showToast(`🎵 Resumed ${resumedCount} tracks`, 'success');
        } else {
            play();
        }
    }).catch(() => play());
};

const stop = () => {
    stopAllAudio();
    state.isPlaying = false;
    updatePlayState();
    stopRealtimeVisualization();
    stopPeriodicSync();
    if (el.seekBar) el.seekBar.value = 0;
    if (el.currentTime) el.currentTime.textContent = '0:00';
    state.pendingSeekPosition = null;
    state.storedSeekTime = null;
    state.originalFilePosition = 0;
    showToast('Stopped', 'info');
};

const seek = () => {
    const seekPercent = el.seekBar.value;

    // Handle seek for original file (when it's the active player)
    // Check if original audio is actually loaded and being used (not just exists)
    if (window.originalAudioPlayer &&
        window.originalAudioPlayer.src &&
        window.originalAudioPlayer.duration &&
        !isNaN(window.originalAudioPlayer.duration) &&
        state.selectedTracks.length === 0) {
        const seekTime = (seekPercent / 100) * window.originalAudioPlayer.duration;
        if (!isNaN(seekTime) && seekTime >= 0 && seekTime <= window.originalAudioPlayer.duration) {
            window.originalAudioPlayer.currentTime = seekTime;
        }
        return;
    }

    // For track-based audio (playing or paused)
    const allAudio = document.querySelectorAll('audio[data-track]');
    if (allAudio.length > 0) {
        let mainAudio = null;
        for (const audio of allAudio) {
            if (audio.duration && !isNaN(audio.duration) && audio.duration > 0) {
                mainAudio = audio;
                break;
            }
        }

        if (mainAudio) {
            const seekTime = (seekPercent / 100) * mainAudio.duration;
            if (!isNaN(seekTime) && seekTime >= 0 && seekTime <= mainAudio.duration) {
                allAudio.forEach(audio => {
                    if (audio.duration && !isNaN(audio.duration) && audio.duration > 0) {
                        const targetSeekTime = (seekPercent / 100) * audio.duration;
                        if (!isNaN(targetSeekTime) && targetSeekTime >= 0 && targetSeekTime <= audio.duration) {
                            audio.currentTime = targetSeekTime;
                        }
                    }
                });
                state.pendingSeekPosition = null;
                state.storedSeekTime = null;
                updateProgress();
                return;
            }
        }

        // If audio not ready yet, store position for when it loads
        state.pendingSeekPosition = seekPercent;
    } else if (state.uploadedFile?.name) {
        // No tracks selected but there's an uploaded file - store seek position for when we play it
        state.pendingSeekPosition = seekPercent;
    }
};

const togglePlayPause = () => {
    if (state.isPlaying) {
        pause();
    } else {
        const existingAudio = document.querySelectorAll('audio[data-track]');
        if (existingAudio.length > 0) {
            resume();
        } else {
            play();
        }
    }
};

/* ==================== UPDATE FUNCTIONS ==================== */

const updateProgress = () => {
    const allAudio = document.querySelectorAll('audio[data-track]');
    let mainAudio = null;
    if (state.selectedTracks.length === 0 && window.originalAudioPlayer &&
        !window.originalAudioPlayer.paused &&
        window.originalAudioPlayer.duration && !isNaN(window.originalAudioPlayer.duration)) {
        mainAudio = window.originalAudioPlayer;
    }
    if (!mainAudio && allAudio.length > 0) {
        for (const audio of allAudio) {
            if (!audio.paused && audio.duration && !isNaN(audio.duration)) {
                mainAudio = audio;
                break;
            }
        }
    }
    if (!mainAudio && allAudio.length > 0) {
        for (const audio of allAudio) {
            if (audio.duration && !isNaN(audio.duration)) {
                mainAudio = audio;
                break;
            }
        }
    }
    if (!mainAudio && state.selectedTracks.length === 0 && window.originalAudioPlayer &&
        window.originalAudioPlayer.duration && !isNaN(window.originalAudioPlayer.duration)) {
        mainAudio = window.originalAudioPlayer;
    }
    if (mainAudio && mainAudio.duration && !isNaN(mainAudio.duration)) {
        const progress = (mainAudio.currentTime / mainAudio.duration) * 100;
        if (el.seekBar) el.seekBar.value = progress;
        if (el.currentTime) el.currentTime.textContent = formatTime(mainAudio.currentTime);
    }
    if (state.isPlaying && allAudio.length > 1) {
        syncAllAudio();
    }
};

const updateDuration = () => {
    const allAudio = document.querySelectorAll('audio[data-track]');
    let mainAudio = null;
    if (state.selectedTracks.length === 0 && window.originalAudioPlayer &&
        window.originalAudioPlayer.duration && !isNaN(window.originalAudioPlayer.duration)) {
        mainAudio = window.originalAudioPlayer;
    }
    if (!mainAudio && allAudio.length > 0) {
        for (const audio of allAudio) {
            if (audio.duration && !isNaN(audio.duration)) {
                mainAudio = audio;
                break;
            }
        }
    }
    if (!mainAudio && state.selectedTracks.length === 0 && window.originalAudioPlayer &&
        window.originalAudioPlayer.duration && !isNaN(window.originalAudioPlayer.duration)) {
        mainAudio = window.originalAudioPlayer;
    }
    if (mainAudio && mainAudio.duration && !isNaN(mainAudio.duration)) {
        if (el.totalTime) el.totalTime.textContent = formatTime(mainAudio.duration);
        drawStaticWaveform();
    }
};

const updateTotalTimeForSelectedTracks = () => {
    if (!el.totalTime || state.selectedTracks.length === 0) return;
    const firstSelected = state.selectedTracks[0];
    if (firstSelected?.track?.duration) {
        el.totalTime.textContent = formatTime(firstSelected.track.duration);
    }
};

const handleTrackEnd = () => {
    if (!state.isLooping) {
        stopRealtimeVisualization();
        state.isPlaying = false;
        updatePlayState();
        state.pendingSeekPosition = null;
        state.storedSeekTime = null;
    }
};

const updatePlayState = () => {
    if (!el.playPauseBtn) return;
    const hasAudio = state.selectedTracks.length > 0 ||
                     state.uploadedFile !== null ||
                     (window.originalAudioPlayer && window.originalAudioPlayer.src);
    if (hasAudio) {
        el.playPauseBtn.disabled = false;
        el.playPauseBtn.style.opacity = '1';
        if (state.isPlaying) {
            if (el.playPauseIcon) el.playPauseIcon.textContent = '⏸';
            el.playPauseBtn.style.background = 'rgba(251, 191, 36, 0.25)';
            el.playPauseBtn.style.borderColor = 'rgba(251, 191, 36, 0.6)';
            el.playPauseBtn.style.boxShadow = '0 0 15px rgba(251, 191, 36, 0.3)';
        } else {
            if (el.playPauseIcon) el.playPauseIcon.textContent = '▶';
            el.playPauseBtn.style.background = '';
            el.playPauseBtn.style.borderColor = '';
            el.playPauseBtn.style.boxShadow = '';
        }
    } else {
        el.playPauseBtn.disabled = true;
        el.playPauseBtn.style.opacity = '0.5';
        el.playPauseBtn.style.background = '';
        el.playPauseBtn.style.borderColor = '';
        el.playPauseBtn.style.boxShadow = '';
        if (el.playPauseIcon) el.playPauseIcon.textContent = '▶';
    }
    if (el.stopBtn) {
        if (hasAudio) {
            el.stopBtn.disabled = false;
            el.stopBtn.style.opacity = '1';
            el.stopBtn.style.background = 'rgba(239, 68, 68, 0.2)';
            el.stopBtn.style.borderColor = 'rgba(239, 68, 68, 0.5)';
            el.stopBtn.style.boxShadow = '0 0 15px rgba(239, 68, 68, 0.3)';
        } else {
            el.stopBtn.disabled = true;
            el.stopBtn.style.opacity = '0.6';
            el.stopBtn.style.background = '';
            el.stopBtn.style.borderColor = '';
            el.stopBtn.style.boxShadow = '';
        }
    }
};

const enablePlayerControls = (enabled) => {
    [el.playPauseBtn, el.stopBtn, el.seekBar].forEach(control => {
        if (control) control.disabled = !enabled;
    });
};

/* ==================== TRACK MANAGEMENT ==================== */

const getTrackIconInfo = (trackName) => {
    const name = trackName.toLowerCase();
    if (name.includes('drum')) return { icon: '🥁', class: 'drum', displayName: 'Drums' };
    if (name.includes('bass')) return { icon: '🎸', class: 'bass', displayName: 'Bass' };
    if (name.includes('vocal')) return { icon: '🎤', class: 'vocals', displayName: 'Vocals' };
    if (name.includes('piano')) return { icon: '🎹', class: 'piano', displayName: 'Piano' };
    if (name.includes('guitar')) return { icon: '🎸', class: 'guitar', displayName: 'Guitar' };
    if (name.includes('other')) return { icon: '🎵', class: 'other', displayName: 'Other' };
    return { icon: '🎶', class: 'other', displayName: 'Track' };
};

const showTrackSkeletonLoading = (count = 3) => {
    const skeletons = [];
    for (let i = 0; i < count; i++) {
        skeletons.push(`
            <div class="skeleton-track" style="animation: fadeIn 0.3s ease forwards; animation-delay: ${i * 50}ms;">
                <div class="skeleton-icon"></div>
                <div class="skeleton-info">
                    <div class="skeleton-line" style="width: 70%;"></div>
                    <div class="skeleton-line short"></div>
                </div>
            </div>
        `);
    }
    el.trackList.innerHTML = skeletons.join('');
};

const updateSidebarTitleCount = (count) => {
    if (!el.sidebarTitleCount) return;
    if (count > 0) {
        el.sidebarTitleCount.textContent = `${count} stems`;
        el.sidebarTitleCount.classList.remove('hidden');
        el.sidebarTitleCount.classList.add('visible');
    } else {
        el.sidebarTitleCount.classList.add('hidden');
        el.sidebarTitleCount.classList.remove('visible');
    }
};

const setupTrackCardListeners = (trackCard, track, index) => {
    trackCard.addEventListener('click', (e) => {
        if (e.target.closest('button[data-action="analyze"]') || e.target.closest('.track-volume-slider')) return;
        const isSelected = state.selectedTracks.some(t => t.track.name === track.name);
        if (isSelected) removeFromSelectedTracks(index);
        else addToSelectedTracks(track, index);
    });
    const analyzeBtn = trackCard.querySelector('button[data-action="analyze"]');
    if (analyzeBtn) analyzeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        analyzeTrack(track);
    });
    const volumeSlider = trackCard.querySelector('.track-volume-slider');
    if (volumeSlider) {
        volumeSlider.addEventListener('click', (e) => e.stopPropagation());
        volumeSlider.addEventListener('input', (e) => {
            e.stopPropagation();
            const trackName = e.target.dataset.track;
            const volume = parseInt(e.target.value);
            state.trackVolumes[trackName] = volume;
            const selectedTrack = state.selectedTracks.find(t => t.track.name === trackName);
            if (selectedTrack) selectedTrack.volume = volume;
            const audioElement = document.querySelector(`audio[data-track="${trackName}"]`);
            if (audioElement) audioElement.volume = volume / 100;
            console.log(`Volume for ${trackName}: ${volume}%`);
        });
    }
};

const addToSelectedTracks = (track, index) => {
    if (state.selectedTracks.some(t => t.track.name === track.name)) return;
    if (state.trackVolumes[track.name] === undefined) state.trackVolumes[track.name] = 50;
    state.selectedTracks.push({ track, index, volume: state.trackVolumes[track.name] });
    const card = document.querySelector(`[data-index="${index}"]`);
    if (card) card.classList.add('active');
    updateTotalTimeForSelectedTracks();
    updateNowPlayingDisplay();
    if (state.isPlaying) {
        const originalIsPlaying = window.originalAudioPlayer && !window.originalAudioPlayer.paused;
        let targetPosition = null;
        if (originalIsPlaying) {
            targetPosition = window.originalAudioPlayer.currentTime;
            window.originalAudioPlayer.pause();
            window.originalAudioPlayer.currentTime = 0;
        }
        if (targetPosition === null) targetPosition = getCurrentPlaybackPosition();
        playTrackImmediately(track, targetPosition);
        state.storedSeekTime = null;
        setTimeout(() => {
            if (state.isPlaying) syncAllAudio();
        }, 100);
    }
    showToast(`Added: ${track.name}`, 'success');
};

const removeFromSelectedTracks = (index) => {
    const trackToRemove = state.selectedTracks.find(t => t.index === index);
    if (!trackToRemove) return;
    state.selectedTracks = state.selectedTracks.filter(t => t.index !== index);
    const card = document.querySelector(`[data-index="${index}"]`);
    if (card) card.classList.remove('active');
    if (state.selectedTracks.length === 0) {
        if (state.uploadedFile?.duration) {
            if (el.totalTime) el.totalTime.textContent = formatTime(state.uploadedFile.duration);
        } else if (window.originalAudioPlayer && window.originalAudioPlayer.duration) {
            if (el.totalTime) el.totalTime.textContent = formatTime(window.originalAudioPlayer.duration);
        } else {
            if (el.totalTime) el.totalTime.textContent = '0:00';
        }
    } else {
        updateTotalTimeForSelectedTracks();
    }
    updateNowPlayingDisplay();
    const audioElement = document.querySelector(`audio[data-track="${trackToRemove.track.name}"]`);
    if (audioElement) {
        if (audioElement.paused && audioElement.currentTime > 0) {
            state.storedSeekTime = audioElement.currentTime;
        }
        audioElement.pause();
        audioElement.remove();
    }
    showToast(`Removed: ${trackToRemove.track.name}`, 'info');
};

const renderTrackList = (tracks) => {
    const separatedTracks = tracks.filter(track => track.is_separated);
    const hasSeparatedTracks = separatedTracks.length > 0;
    updateSidebarTitleCount(hasSeparatedTracks ? separatedTracks.length : 0);
    if (el.guideCard) {
        if (hasSeparatedTracks) el.guideCard.classList.remove('hidden');
        else el.guideCard.classList.add('hidden');
    }
    if (!hasSeparatedTracks) {
        const originalFile = tracks.find(track => !track.is_separated);
        if (originalFile) {
            el.trackList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎵</div>
                    <h3>Original File Ready</h3>
                    <p class="filename">${originalFile.name}</p>
                    <p class="guide-subtext">💡 <strong>Play full song</strong> - Click play to listen</p>
                    <p class="guide-subtext">💡 <strong>Separate tracks</strong> - Use the "Start Separation" button above</p>
                </div>
            `;
        } else {
            el.trackList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎵</div>
                    <h3>Ready to Process</h3>
                    <p>Uploaded file is ready</p>
                </div>
            `;
        }
        return;
    }
    el.trackList.innerHTML = '';
    separatedTracks.forEach((track, index) => {
        const trackInfo = getTrackIconInfo(track.name);
        const trackCard = document.createElement('div');
        let cardClasses = `track-card fade-in ${trackInfo.class}`;
        trackCard.className = cardClasses;
        trackCard.style.animationDelay = `${index * 0.05}s`;
        trackCard.dataset.index = index;
        trackCard.dataset.type = trackInfo.class;
        const isSelected = state.selectedTracks.some(t => t.track.name === track.name);
        if (isSelected) trackCard.classList.add('active');
        const duration = formatTime(track.duration);
        const sizeMB = (track.size / (1024 * 1024)).toFixed(1);
        const storedVolume = state.trackVolumes[track.name] ?? 50;
        trackCard.innerHTML = `
            <div class="track-icon">${trackInfo.icon}</div>
            <div class="track-info">
                <div class="track-name">${track.name}</div>
                <div class="track-meta">
                    <span>⏱️ ${duration}</span>
                    <span>💾 ${sizeMB} MB</span>
                    <span>🎵 ${track.channels === 2 ? 'Stereo' : 'Mono'}</span>
                    <span> Hz ${track.samplerate}</span>
                </div>
            </div>
            <div class="track-actions">
                <button class="btn-glow" data-action="analyze" title="Analyze">📊</button>
                <div class="track-volume-container">
                    <input type="range" class="track-volume-slider" min="0" max="100" value="${storedVolume}"
                           data-track="${track.name}" data-index="${index}" orient="vertical" title="Volume">
                </div>
            </div>
        `;
        setupTrackCardListeners(trackCard, track, index);
        el.trackList.appendChild(trackCard);
    });
};

const analyzeTrack = async (track) => {
    if (!state.apiConnected) {
        showToast('API not connected', 'error');
        return;
    }
    showToast('Analyzing...', 'info');
    try {
        const audioUrl = `${API_BASE_URL}/tracks/audio/${track.name}`;
        const audioResponse = await fetch(audioUrl);
        if (!audioResponse.ok) throw new Error('Unable to download audio file');
        const audioBlob = await audioResponse.blob();
        const formData = new FormData();
        const audioFile = new File([audioBlob], track.name, { type: 'audio/wav' });
        formData.append('file', audioFile);
        const analyzeResponse = await fetch(`${API_BASE_URL}/analysis/analyze`, {
            method: 'POST',
            body: formData,
        });
        if (!analyzeResponse.ok) throw new Error(`HTTP ${analyzeResponse.status}`);
        const result = await analyzeResponse.json();
        if (result.status === 'success') {
            const analysis = result.analysis;
            el.analysisCard.classList.remove('hidden');
            el.statBpm.textContent = analysis.bpm;
            el.statStyle.textContent = analysis.style;
            el.statMood.textContent = analysis.mood;
            el.statEnergy.textContent = `${(analysis.energy * 100).toFixed(0)}%`;
            el.statKey.textContent = analysis.key;
            el.bpmValue.textContent = analysis.bpm;
            el.bpmBadge.classList.remove('hidden');
            showToast(`✅ Analysis complete: ${analysis.bpm} BPM | ${analysis.style} | ${analysis.mood}`, 'success');
        } else {
            showToast('Analysis failed', 'error');
        }
    } catch (error) {
        console.error('Analysis error:', error);
        showToast(`Analysis failed: ${error.message}`, 'error');
    }
};

const loadTracks = async (options = {}) => {
    if (!state.apiConnected) {
        showToast('API not connected', 'error');
        showConnectionHelp();
        return;
    }
    showTrackSkeletonLoading(3);
    try {
        const url = `${API_BASE_URL}/tracks/list?t=${Date.now()}`;
        const response = await fetch(url, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache' }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        const data = await response.json();
        state.tracks = data;
        if (!data || data.length === 0) {
            el.trackList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎵</div>
                    <h3>No Tracks</h3>
                    <p>Click the + button above to upload audio</p>
                    <p class="guide-subtext">💡 Play directly after upload, or click "Process" to separate drums</p>
                </div>
            `;
            if (el.uploadPanel) {
                el.uploadPanel.classList.remove('hidden');
                if (el.uploadBtn) {
                    el.uploadBtn.disabled = false;
                    el.uploadBtn.textContent = '+ Upload';
                }
                state.uploadVisible = true;
                state.uploadLocked = false;
            }
            if (el.guideCard) el.guideCard.classList.add('hidden');
            updateSidebarTitleCount(0);
            return;
        }
        renderTrackList(data);
        enablePlayerControls(true);
        if (el.uploadPanel) {
            el.uploadPanel.classList.add('hidden');
            state.uploadVisible = false;
            state.uploadLocked = true;
            if (el.uploadBtn) {
                el.uploadBtn.disabled = true;
                el.uploadBtn.textContent = 'Processed';
            }
        }
        const originalFile = data.find(track => !track.is_separated);
        if (originalFile) {
            state.uploadedFile = {
                name: originalFile.name, path: originalFile.path, size: originalFile.size,
                duration: originalFile.duration, source: originalFile.source || 'upload',
                isSeparated: false
            };
        }
        if (options.showAddedMessage) {
            showToast(`✅ Loaded ${data.length} tracks`, 'success');
        } else {
            showToast(`Loaded ${data.length} tracks`, 'success');
        }
        if (state.uploadedFile) {
            updateNowPlayingDisplay();
            if (el.totalTime && state.uploadedFile.duration) {
                el.totalTime.textContent = formatTime(state.uploadedFile.duration);
            }
        }
    } catch (error) {
        console.error('Error loading tracks:', error);
        el.trackList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <h3>Load Failed</h3>
                <p>${error.message}</p>
                <button id="retryBtn" class="btn-secondary">Retry</button>
            </div>
        `;
        const retryBtn = document.getElementById('retryBtn');
        if (retryBtn) retryBtn.addEventListener('click', loadTracks);
        showToast(`Load failed: ${error.message}`, 'error');
    }
};

/* ==================== NOW PLAYING DISPLAY ==================== */

const generateSongInfoBar = (fileInfo = null, source = null) => {
    const info = fileInfo || state.uploadedFile;
    if (!info) return '';
    const extension = info.name.split('.').pop() || 'Unknown format';
    const truncatedName = info.name.length > 30 ? info.name.substring(0, 30) + '...' : info.name;
    const src = source || info.source || 'upload';
    const sourceBadge = src === 'youtube'
        ? '<span class="song-info-source">YouTube</span>'
        : '<span class="song-info-source">Local</span>';
    return `
        <div class="song-info-bar">
            <div class="song-info-icon">🎵</div>
            <div class="song-info-details">
                <div class="song-info-item">
                    <span class="song-info-label">File</span>
                    <span class="song-info-value truncated" title="${info.name}">${truncatedName}</span>
                </div>
                <div class="song-info-item">
                    <span class="song-info-label">Duration</span>
                    <span class="song-info-value">${formatTime(info.duration)}</span>
                </div>
                <div class="song-info-item">
                    <span class="song-info-label">Format</span>
                    <span class="file-badge">${extension.toUpperCase()}</span>
                </div>
                ${sourceBadge}
            </div>
        </div>
    `;
};

const updateNowPlayingDisplay = () => {
    if (!el.nowPlayingContent) return;
    let songInfoHTML = '';
    if (state.uploadedFile && state.uploadedFile.name) {
        songInfoHTML = generateSongInfoBar(state.uploadedFile);
    }
    if (state.selectedTracks.length === 0) {
        let playOriginalHTML = '';
        if (state.uploadedFile && state.uploadedFile.name) {
            playOriginalHTML = `
                <button id="playOriginalBtn" class="btn-primary" style="flex: 1; min-width: 140px; padding: 10px 24px; height: 48px; display: inline-flex; align-items: center; justify-content: center;">
                    <span class="icon">▶</span> Play full song
                </button>
            `;
            if (el.totalTime && state.uploadedFile.duration) {
                el.totalTime.textContent = formatTime(state.uploadedFile.duration);
            }
        } else {
            playOriginalHTML = `
                <span class="placeholder-text">
                    <span class="icon">🎵</span>
                    Select tracks to play
                </span>
            `;
        }
        el.nowPlayingContent.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
                ${songInfoHTML}
                <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: center; min-height: 48px; height: 48px;">
                    ${playOriginalHTML}
                </div>
            </div>
        `;
        if (state.uploadedFile && state.uploadedFile.name) {
            const playOriginalBtn = document.getElementById('playOriginalBtn');
            if (playOriginalBtn) playOriginalBtn.addEventListener('click', () => play());
        }
        return;
    }
    const groupedTracks = state.selectedTracks.reduce((acc, t) => {
        const info = getTrackIconInfo(t.track.name);
        if (!acc[info.class]) acc[info.class] = { icon: info.icon, class: info.class, displayName: info.displayName, count: 0 };
        acc[info.class].count++;
        return acc;
    }, {});
    const badges = Object.values(groupedTracks)
        .map(g => `<span class="track-icon-badge ${g.class}"><span class="icon">${g.icon}</span> ${g.displayName}${g.count > 1 ? `×${g.count}` : ''}</span>`)
        .join(' ');
    el.nowPlayingContent.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
            ${songInfoHTML}
            <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: center; min-height: 48px; height: 48px;">
                ${badges}
            </div>
        </div>
    `;
};

const showProcessingInNowPlayingCard = (message, percentage, current, total) => {
    if (!el.nowPlayingContent) return;
    const displayMessage = message || 'Processing...';
    const progressWidth = percentage !== undefined ? percentage : 0;
    const details = (current !== undefined && total !== undefined && total > 0)
        ? `Progress: ${current}/${total} (${Math.round((current / total) * 100)}%)`
        : '';
    let songInfoHTML = '';
    if (state.uploadedFile && state.uploadedFile.name) {
        songInfoHTML = generateSongInfoBar(state.uploadedFile);
    }
    el.nowPlayingContent.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
            ${songInfoHTML}
            <div class="processing-content">
                <div style="font-size: 1.25rem; font-weight: 700; color: var(--accent); margin-bottom: 12px;">
                    ⏳ ${displayMessage}
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progressWidth}%"></div>
                    </div>
                </div>
                ${details ? `<div style="margin-top: 8px; font-size: 0.9rem; color: var(--text-secondary);">${details}</div>` : ''}
            </div>
        </div>
    `;
    if (el.nowPlayingHeader) el.nowPlayingHeader.textContent = '⏳ Separating...';
};

const hideProcessingInNowPlayingCard = () => {
    if (!el.nowPlayingContent) return;
    el.nowPlayingContent.innerHTML = '<div class="placeholder-text">Select tracks to play</div>';
    if (el.nowPlayingHeader) el.nowPlayingHeader.textContent = '🎶 Now Playing';
};

const showPreviewInNowPlayingCard = (fileInfo, showProcessButton = true) => {
    if (!el.nowPlayingContent) return;
    const source = fileInfo.source || 'upload';
    const buttonText = 'Start Separation';
    const buttonClass = 'btn-primary';
    const processButtonHTML = showProcessButton ? `
        <div style="display: flex; gap: 8px; margin-top: var(--space-md);">
            <button id="processNowBtn" class="${buttonClass}" style="flex: 1;">${buttonText}</button>
        </div>
    ` : '';
    el.nowPlayingContent.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
            ${generateSongInfoBar(fileInfo, source)}
            <div style="text-align: center; color: var(--text-muted); font-size: 0.95rem; margin-top: 4px;">
                🎧 Click the button below to start separation
            </div>
            ${processButtonHTML}
        </div>
    `;
    if (el.nowPlayingHeader) el.nowPlayingHeader.textContent = '🎵 File Preview';
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) {
        uploadDropzone.classList.remove('uploaded', 'disabled');
        uploadDropzone.classList.add('uploaded');
    }
    if (showProcessButton) {
        const processNowBtn = document.getElementById('processNowBtn');
        if (processNowBtn) processNowBtn.addEventListener('click', processUploadedFile);
    }
};

const clearPreviewFromNowPlayingCard = () => {
    if (!el.nowPlayingContent) return;
    el.nowPlayingContent.innerHTML = '<div class="placeholder-text">Select tracks to play</div>';
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) uploadDropzone.classList.remove('uploaded', 'disabled');
};

/* ==================== UPLOAD & PROCESSING ==================== */

const clearSelection = async () => {
    console.log('=== clearSelection() called ===');
    if (state.isPlaying) stopAllAudio();
    if (state.apiConnected) {
        try {
            const response = await fetch(`${API_BASE_URL}/separation/clear`, { method: 'POST' });
            if (response.ok) showToast('All uploaded files cleared', 'success');
            else showToast('Clear failed', 'error');
        } catch (error) {
            console.error('Clear error:', error);
            showToast(`Clear failed: ${error.message}`, 'error');
        }
    }
    state.selectedTracks.forEach(selected => {
        const card = document.querySelector(`[data-index="${selected.index}"]`);
        if (card) card.classList.remove('active');
    });
    state.selectedTracks = [];
    state.uploadLocked = false;
    state.uploadedFile = { name: null, path: null, size: null, duration: null, source: null, timestamp: null, isSeparated: false };
    state.processing = false;
    state.processingType = null;
    state.pendingSeekPosition = null;
    state.storedSeekTime = null;
    if (el.trackList) {
        el.trackList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🎵</div>
                <h3>No Tracks</h3>
                <p>Click the + button above to upload audio</p>
                <button id="emptyRefreshBtn" class="btn-secondary">Refresh</button>
            </div>
        `;
        const emptyRefreshBtn = document.getElementById('emptyRefreshBtn');
        if (emptyRefreshBtn) {
            emptyRefreshBtn.addEventListener('click', () => {
                if (state.apiConnected) {
                    loadTracks();
                    showToast('Track list refreshed', 'success');
                }
            });
        }
    }
    if (el.guideCard) el.guideCard.classList.add('hidden');
    updateSidebarTitleCount(0);
    if (el.totalTime) el.totalTime.textContent = '0:00';
    if (el.seekBar) el.seekBar.value = 0;
    if (el.currentTime) el.currentTime.textContent = '0:00';
    if (el.nowPlayingContent) el.nowPlayingContent.innerHTML = '<div class="placeholder-text">Select tracks to play</div>';
    stopRealtimeVisualization();
    if (el.uploadPanel) {
        el.uploadPanel.classList.remove('hidden');
        if (el.uploadBtn) {
            el.uploadBtn.disabled = false;
            el.uploadBtn.textContent = '+ Upload';
        }
        state.uploadVisible = true;
        state.uploadLocked = false;
    }
    clearPreviewFromNowPlayingCard();
    if (el.fileInput) el.fileInput.value = '';
    if (el.uploadProgress) el.uploadProgress.classList.add('hidden');
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) uploadDropzone.classList.remove('hidden');
    if (el.processCard) el.processCard.classList.add('hidden');
    if (el.uploadPanel) el.uploadPanel.classList.remove('processing');
    updatePlayState();
};

const uploadFileForPreview = async (file) => {
    if (!state.apiConnected) {
        showToast('API not connected', 'error');
        return;
    }
    if (state.uploadedFile && state.uploadedFile.name) {
        console.log('Clearing existing uploaded file before new upload:', state.uploadedFile.name);
        try {
            await fetch(`${API_BASE_URL}/separation/clear`, { method: 'POST' });
            state.uploadedFile = { name: null, path: null, size: null, duration: null, source: null, timestamp: null, isSeparated: false };
        } catch (clearError) {
            console.warn('Failed to clear existing files:', clearError);
        }
    }
    state.processing = true;
    state.processingType = 'upload';
    state.isUploading = true;
    if (el.uploadBtn) {
        el.uploadBtn.disabled = true;
        el.uploadBtn.textContent = '⏳ Uploading';
    }
    const formData = new FormData();
    formData.append('file', file);
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) uploadDropzone.classList.add('hidden');
    el.uploadProgress.classList.remove('hidden');
    updateProgressUI('Uploading...', 20);
    try {
        const response = await fetch(`${API_BASE_URL}/upload/preview`, { method: 'POST', body: formData });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        if (result.status === 'success') {
            updateProgressUI('Upload complete', 50);
            showFilePreviewFromServer(result.file_info);
            state.uploadedFile = {
                name: result.file_info.name,
                path: `storage/uploaded/${result.file_info.name}`,
                size: result.file_info.size,
                duration: result.file_info.duration,
                source: 'upload',
                timestamp: Date.now(),
                isSeparated: false,
            };
            showToast('File uploaded, click to process', 'success');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast(`Upload failed: ${error.message}`, 'error');
        updateProgressUI('Upload failed', 0);
        setTimeout(() => cancelFilePreview(), 2000);
    } finally {
        state.isUploading = false;
        state.processing = false;
        state.processingType = null;
        if (el.uploadBtn) {
            el.uploadBtn.disabled = false;
            el.uploadBtn.textContent = '+ Upload';
        }
    }
};

const showFilePreviewFromServer = (fileInfo) => {
    if (el.uploadProgress) el.uploadProgress.classList.add('hidden');
    if (el.processCard) el.processCard.classList.add('hidden');
    if (el.uploadPanel) el.uploadPanel.classList.add('hidden');
    state.uploadVisible = false;
    showPreviewInNowPlayingCard(fileInfo, true);
};

const cancelFilePreview = () => {
    state.uploadedFile = { name: null, path: null, size: null, duration: null, source: null, timestamp: null, isSeparated: false };
    if (el.fileInput) el.fileInput.value = '';
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) uploadDropzone.classList.remove('hidden');
    if (el.processCard) el.processCard.classList.add('hidden');
    if (el.uploadProgress) el.uploadProgress.classList.add('hidden');
    if (el.uploadPanel) el.uploadPanel.classList.remove('processing');
    clearPreviewFromNowPlayingCard();
    showToast('Selection cancelled', 'info');
};

const processUploadedFile = async () => {
    if (!state.uploadedFile?.name) {
        showToast('Please upload or download an audio file first', 'warning');
        return;
    }
    if (!state.apiConnected) {
        showToast('API not connected', 'error');
        return;
    }
    try {
        const checkResponse = await fetch(`${API_BASE_URL}/tracks/info/${encodeURIComponent(state.uploadedFile.name)}`);
        if (!checkResponse.ok) {
            showToast('File expired, please re-upload', 'error');
            state.uploadedFile = { name: null, path: null, size: null, duration: null, source: null, timestamp: null, isSeparated: false };
            clearPreviewFromNowPlayingCard();
            return;
        }
    } catch (error) {
        console.warn('File existence check failed:', error);
    }
    state.processing = true;
    state.processingType = 'separation';
    if (el.uploadProgress) el.uploadProgress.classList.add('hidden');
    const formData = new FormData();
    formData.append('filename', state.uploadedFile.name);
    if (el.confirmUploadBtn) {
        el.confirmUploadBtn.disabled = true;
        el.confirmUploadBtn.textContent = 'Processing...';
        el.confirmUploadBtn.style.opacity = '0.6';
        el.confirmUploadBtn.style.cursor = 'not-allowed';
    }
    if (el.cancelUploadBtn) el.cancelUploadBtn.disabled = true;
    if (el.uploadPanel) el.uploadPanel.classList.add('processing');
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) {
        uploadDropzone.classList.remove('uploaded');
        uploadDropzone.classList.add('disabled');
    }
    if (window.originalAudioPlayer && !window.originalAudioPlayer.paused) {
        window.originalAudioPlayer.pause();
    }
    state.isPlaying = false;
    updatePlayState();
    showProcessingInNowPlayingCard('Preparing separation...', 0, 0, 0);
    try {
        const response = await fetch(`${API_BASE_URL}/separation/separate_by_name_stream`, {
            method: 'POST',
            body: formData,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        const processStream = async () => {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split('\n\n');
                buffer = events.pop();
                for (const event of events) {
                    if (event.startsWith('data: ')) {
                        const dataStr = event.slice(6);
                        try {
                            const data = JSON.parse(dataStr);
                            handleProgressUpdate(data);
                        } catch (e) {
                            console.warn('Failed to parse progress data:', e);
                        }
                    }
                }
            }
        };
        await processStream();
    } catch (error) {
        console.error('Separation error:', error);
        showToast(`Separation failed: ${error.message}`, 'error');
        hideProcessingInNowPlayingCard();
        if (el.uploadPanel) el.uploadPanel.classList.remove('processing');
        const uploadDropzone = document.querySelector('.upload-dropzone');
        if (uploadDropzone) {
            uploadDropzone.classList.remove('disabled');
            uploadDropzone.classList.add('uploaded');
        }
        if (el.confirmUploadBtn) {
            el.confirmUploadBtn.disabled = false;
            el.confirmUploadBtn.textContent = 'Process';
            el.confirmUploadBtn.style.opacity = '1';
            el.confirmUploadBtn.style.cursor = 'pointer';
        }
        if (el.cancelUploadBtn) el.cancelUploadBtn.disabled = false;
        state.processing = false;
        state.processingType = null;
    }
};

const handleProgressUpdate = (data) => {
    const { stage, current, total, message, percentage, status } = data;
    showProcessingInNowPlayingCard(message, percentage, current, total);
    console.log(`Progress [${stage}]: ${current}/${total} - ${message}`);
    if (stage === 'complete' || status === 'success') {
        if (state.uploadedFile && state.uploadedFile.name) state.uploadedFile.isSeparated = true;
        state.processing = false;
        state.processingType = null;
        updateAfterSeparation().then(() => {
            console.log('Separation completed and UI updated');
            showToast('✅ Separation complete!', 'success');
        });
    }
    if (stage === 'error' || status === 'error') {
        showToast(`Separation failed: ${data.message}`, 'error');
        hideProcessingInNowPlayingCard();
        if (el.uploadPanel) el.uploadPanel.classList.remove('processing');
        const uploadDropzone = document.querySelector('.upload-dropzone');
        if (uploadDropzone) {
            uploadDropzone.classList.remove('disabled');
            uploadDropzone.classList.add('uploaded');
        }
        if (el.confirmUploadBtn) {
            el.confirmUploadBtn.disabled = false;
            el.confirmUploadBtn.textContent = 'Process';
            el.confirmUploadBtn.style.opacity = '1';
            el.confirmUploadBtn.style.cursor = 'pointer';
        }
        if (el.cancelUploadBtn) el.cancelUploadBtn.disabled = false;
    }
};

const updateAfterSeparation = async () => {
    await loadTracks();
    if (el.processCard) el.processCard.classList.add('hidden');
    if (el.nowPlayingContent) {
        let songInfoHTML = '';
        if (state.uploadedFile) {
            songInfoHTML = generateSongInfoBar(state.uploadedFile, state.uploadedFile.source || 'upload');
        }
        el.nowPlayingContent.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
                ${songInfoHTML}
                <div class="processing-content">
                    <div style="font-size: 1.25rem; font-weight: 700; color: #22c55e; margin-bottom: 12px;">
                        ✅ Separation complete!
                    </div>
                    <div style="font-size: 0.95rem; color: var(--text-secondary);">
                        Separated tracks loaded into track library
                    </div>
                </div>
            </div>
        `;
    }
    if (el.nowPlayingHeader) el.nowPlayingHeader.textContent = '✅ Done';
    await new Promise(resolve => setTimeout(resolve, 1000));
    hideProcessingInNowPlayingCard();
    if (el.nowPlayingHeader) el.nowPlayingHeader.textContent = '🎶 Now Playing';
    updateNowPlayingDisplay();
    state.uploadVisible = false;
    el.uploadPanel.classList.add('hidden');
    state.uploadLocked = true;
    if (el.uploadBtn) {
        el.uploadBtn.disabled = true;
        el.uploadBtn.textContent = '+ Upload';
    }
    console.log('Upload panel folded and locked after separation');
};

const toggleUploadPanel = () => {
    if (state.isUploading) {
        showToast('Upload in progress, please wait', 'warning');
        return;
    }
    if (state.uploadLocked && !state.uploadVisible) {
        showToast('File already uploaded, please clear before uploading a new one', 'warning');
        return;
    }
    state.uploadVisible = !state.uploadVisible;
    if (state.uploadVisible) {
        el.uploadPanel.classList.remove('hidden');
        if (el.uploadBtn) el.uploadBtn.textContent = '✕ Close';
    } else {
        el.uploadPanel.classList.add('hidden');
        if (el.uploadBtn) el.uploadBtn.textContent = '+ Upload';
    }
};

const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 100 * 1024 * 1024) {
        showToast('File too large, maximum 100MB', 'error');
        return;
    }
    if (!file.type.startsWith('audio/')) {
        showToast('Please upload an audio file', 'error');
        return;
    }
    uploadFileForPreview(file);
};

/* ==================== YOUTUBE DOWNLOAD ==================== */

const handleYouTubeDownload = async () => {
    if (!state.apiConnected) {
        showToast('API not connected', 'error');
        return;
    }
    const url = el.youtubeUrl?.value.trim();
    if (!url) {
        showToast('Please enter a YouTube video link', 'warning');
        return;
    }
    if (state.uploadedFile && state.uploadedFile.name) {
        console.log('Clearing existing uploaded file before YouTube download:', state.uploadedFile.name);
        try {
            await fetch(`${API_BASE_URL}/separation/clear`, { method: 'POST' });
            state.uploadedFile = { name: null, path: null, size: null, duration: null, source: null, timestamp: null, isSeparated: false };
        } catch (clearError) {
            console.warn('Failed to clear existing files:', clearError);
        }
    }
    state.processing = true;
    state.processingType = 'download';
    el.youtubeProgress?.classList.remove('hidden');
    updateYouTubeProgressUI('Downloading...', 20);
    try {
        const response = await fetch(`${API_BASE_URL}/youtube/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                url: url, 
                name: el.youtubeName?.value.trim() || null 
            }),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        const result = await response.json();
        if (result.status === 'success') {
            updateYouTubeProgressUI('Download complete!', 100);
            showToast('✅ Download successful!', 'success');
            if (el.youtubeUrl) el.youtubeUrl.value = '';
            if (el.youtubeName) el.youtubeName.value = '';
            state.processing = false;
            state.processingType = null;
            await showYouTubePreview(result.data);
            setTimeout(() => el.youtubeProgress?.classList.add('hidden'), 2000);
        } else {
            throw new Error(result.message || 'Download failed');
        }
    } catch (error) {
        console.error('YouTube download error:', error);
        showToast(`Download failed: ${error.message}`, 'error');
        updateYouTubeProgressUI('Download failed', 0);
        setTimeout(() => el.youtubeProgress?.classList.add('hidden'), 2000);
        state.processing = false;
        state.processingType = null;
    }
};

const showYouTubePreview = async (downloadResult) => {
    const filename = downloadResult.file_path.split('/').pop();
    const duration = downloadResult.duration;
    state.uploadedFile = {
        name: filename,
        path: downloadResult.file_path,
        duration: duration,
        source: 'youtube',
        timestamp: Date.now(),
        isSeparated: false,
        size: downloadResult.size || 0
    };
    state.uploadVisible = false;
    if (el.uploadPanel) el.uploadPanel.classList.add('hidden');
    if (el.processCard) el.processCard.classList.add('hidden');
    if (el.nowPlayingContent) {
        el.nowPlayingContent.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
                ${generateSongInfoBar(state.uploadedFile, 'youtube')}
                <div style="display: flex; gap: 8px; margin-top: 8px;">
                    <button id="playPreviewBtn" class="btn-secondary" style="flex: 1;">▶ Play Preview</button>
                    <button id="separateBtn" class="btn-primary" style="flex: 1;">Separate</button>
                </div>
            </div>
        `;
        const playPreviewBtn = document.getElementById('playPreviewBtn');
        if (playPreviewBtn) playPreviewBtn.addEventListener('click', playOriginalFile);
        const separateBtn = document.getElementById('separateBtn');
        if (separateBtn) separateBtn.addEventListener('click', processUploadedFile);
    }
    if (el.nowPlayingHeader) el.nowPlayingHeader.textContent = '🎵 YouTube Preview';
    if (el.totalTime && duration) el.totalTime.textContent = formatTime(duration);
    if (el.currentTime) el.currentTime.textContent = '0:00';
    if (el.seekBar) el.seekBar.value = 0;
    state.isPlaying = false;
    updatePlayState();
};

/* ==================== UI INITIALIZATION & EVENTS ==================== */

const showConnectionHelp = () => {
    el.trackList.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">⚠️</div>
            <h3>Cannot connect to API</h3>
            <p>Please ensure the FastAPI server is running</p>
            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;">
                Run in terminal:<br>
                <code style="background: var(--bg-tertiary); padding: 4px 8px; border-radius: 4px; display: inline-block; margin-top: 4px;">
                    uv run uvicorn api.server:app --host 0.0.0.0 --port 8000
                </code>
            </p>
            <button id="retryConnectionBtn" class="btn-primary" style="margin-top: 1rem;">Retry Connection</button>
        </div>
    `;
    const retryBtn = document.getElementById('retryConnectionBtn');
    if (retryBtn) retryBtn.addEventListener('click', async () => {
        await checkApiConnection();
        if (state.apiConnected) await loadTracks();
    });
};

const checkApiConnection = async () => {
    console.log('🧪 Starting API connection check...');
    updateApiStatus('connecting', 'Connecting...');
    const healthUrl = `${API_BASE_URL}/health`;
    console.log('📡 Fetching from:', healthUrl);
    try {
        const response = await fetch(healthUrl, {
            method: 'GET',
            mode: 'cors',
            signal: AbortSignal.timeout(5000),
            cache: 'no-cache',
        });
        if (response.ok) {
            const data = await response.json();
            state.apiConnected = true;
            updateApiStatus('connected', `Connected (${data.device.toUpperCase()})`);
            enablePlayerControls(true);
            console.log('✅ API Connected:', data);
            return true;
        } else {
            console.error('❌ HTTP error:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('❌ API connection error:', error);
        console.error('❌ API Base URL attempted:', API_BASE_URL);
        console.error('❌ Current location:', window.location.href);
        console.error('❌ Error name:', error.name);
        console.error('❌ Error message:', error.message);
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            console.error('💡 Likely cause: CORS or network issue');
        }
        if (error.name === 'AbortError') {
            console.error('💡 Likely cause: Server not responding or timeout');
        }
    }
    state.apiConnected = false;
    updateApiStatus('disconnected', 'Disconnected');
    return false;
};

const setupEventListeners = () => {
    if (el.refreshBtn) el.refreshBtn.addEventListener('click', () => {
        if (state.apiConnected) {
            loadTracks();
            showToast('Track list refreshed', 'success');
        } else {
            showToast('API not connected', 'error');
        }
    });
    if (el.clearBtn) el.clearBtn.addEventListener('click', clearSelection);
    if (el.emptyRefreshBtn) el.emptyRefreshBtn.addEventListener('click', () => {
        if (state.apiConnected) {
            loadTracks();
            showToast('Track list refreshed', 'success');
        }
    });
    if (el.uploadBtn) el.uploadBtn.addEventListener('click', toggleUploadPanel);
    if (el.selectFileBtn) el.selectFileBtn.addEventListener('click', () => el.fileInput?.click());
    if (el.fileInput) el.fileInput.addEventListener('change', handleFileSelect);
    if (el.downloadYoutubeBtn) el.downloadYoutubeBtn.addEventListener('click', handleYouTubeDownload);
    if (el.cancelUploadBtn) el.cancelUploadBtn.addEventListener('click', cancelFilePreview);
    const dropzone = document.querySelector('.upload-dropzone');
    if (dropzone) {
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) handleFileSelect({ target: { files } });
        });
        dropzone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (!dropzone.classList.contains('disabled') && el.fileInput) el.fileInput.click();
            }
        });
    }
    if (el.playPauseBtn) el.playPauseBtn.addEventListener('click', togglePlayPause);
    if (el.stopBtn) el.stopBtn.addEventListener('click', stop);
    if (el.seekBar) {
        el.seekBar.addEventListener('input', () => seek());
        el.seekBar.addEventListener('change', () => seek());
        console.log('✅ Seek bar event listeners attached');
    }
    if (el.volumeSlider) {
        el.volumeSlider.addEventListener('input', (e) => {
            const value = e.target.value;
            if (el.audioPlayer) el.audioPlayer.volume = value / 100;
            if (el.volumeValue) el.volumeValue.textContent = `${value}%`;
        });
    }
    if (el.speedSlider) {
        el.speedSlider.addEventListener('input', (e) => {
            const value = e.target.value;
            const speed = value / 100;
            if (el.audioPlayer) el.audioPlayer.playbackRate = speed;
            if (el.speedValue) el.speedValue.textContent = `${speed.toFixed(1)}x`;
        });
    }
    if (el.loopCheckbox) {
        el.loopCheckbox.addEventListener('change', (e) => {
            state.isLooping = e.target.checked;
            if (el.audioPlayer) el.audioPlayer.loop = state.isLooping;
        });
    }
    if (el.audioPlayer) {
        el.audioPlayer.addEventListener('timeupdate', updateProgress);
        el.audioPlayer.addEventListener('loadedmetadata', updateDuration);
        el.audioPlayer.addEventListener('ended', handleTrackEnd);
        el.audioPlayer.addEventListener('play', () => {
            state.isPlaying = true;
            updatePlayState();
            startRealtimeVisualization();
        });
        el.audioPlayer.addEventListener('pause', () => {
            if (state.isPlaying) {
                state.isPlaying = false;
                updatePlayState();
                stopRealtimeVisualization();
            }
        });
        el.audioPlayer.addEventListener('error', (e) => {
            console.error('Audio error:', e);
            showToast('Audio loading failed', 'error');
        });
    }
};

const setupKeyboardShortcuts = () => {
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
        switch (e.code) {
            case 'Space':
                e.preventDefault();
                togglePlayPause();
                break;
            case 'Escape':
                stop();
                break;
            case 'ArrowRight':
                if (state.selectedTracks.length > 0 && el.audioPlayer) {
                    el.audioPlayer.currentTime = Math.min(el.audioPlayer.currentTime + 5, el.audioPlayer.duration || 0);
                }
                break;
            case 'ArrowLeft':
                if (state.selectedTracks.length > 0 && el.audioPlayer) {
                    el.audioPlayer.currentTime = Math.max(el.audioPlayer.currentTime - 5, 0);
                }
                break;
            case 'KeyR':
                if (state.apiConnected) {
                    loadTracks();
                    showToast('Track list refreshed', 'success');
                }
                break;
            case 'KeyU':
                toggleUploadPanel();
                break;
            case 'KeyC':
                clearSelection();
                break;
        }
    });
};

const init = async () => {
    console.log('Initializing Drum Trainer Web App...');
    if (el.waveform) {
        waveformCtx = el.waveform.getContext('2d');
        resizeWaveformCanvas();
        window.addEventListener('resize', resizeWaveformCanvas);
    }
    setupEventListeners();
    setupKeyboardShortcuts();
    const connected = await checkApiConnection();
    if (connected) {
        await loadTracks();
    } else {
        showConnectionHelp();
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Performance-optimized track list rendering with debouncing
const debouncedRenderTrackList = debounce(renderTrackList, 150);
