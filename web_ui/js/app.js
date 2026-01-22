/**
 * Drum Trainer Web App - Modern JavaScript Controller
 * Handles API communication, audio playback, and UI interactions
 *
 * Version: 1.1.0 - Fixed YouTube download flow and original file playback
 * Version: 1.1.1 - Added progress display for separation and seek bar support for preview
 * Version: 1.2.0 - Consolidated processCard into now-playing-card for unified UX
 * Version: 1.2.1 - Fixed "Separate" button disappearing during preview playback
 * Version: 1.2.2 - Keep original file for playback during separation (copy instead of move)
 * Version: 2.0.0 - Unified file state management: uploadedFile state replaces selectedFile
 *                 - Added clear-before-upload logic (one file at a time)
 *                 - Created processUploadedFile() unified function (replaces processSelectedFile + separateYouTubeFile)
 *                 - Added file existence validation before processing
 *                 - Added processing state tracking (processing, processingType)
 */

// Detect API base URL dynamically
function getApiBaseUrl() {
    const origin = window.location.origin;
    const pathname = window.location.pathname;

    console.log('Window location debug:', {
        origin: origin,
        pathname: pathname,
        href: window.location.href
    });

    // Check if we're being served from FastAPI's /ui endpoint
    // The API is at the same origin (root level), not at /ui
    if (pathname.startsWith('/ui')) {
        console.log('Detected /ui path, using origin:', origin);
        return origin; // Same origin, API at root (http://localhost:8000)
    }

    // Default for development (when opening HTML directly)
    console.log('Using default API URL: http://localhost:8000');
    return 'http://localhost:8000';
}

const API_BASE_URL = getApiBaseUrl();

console.log('✅ API Base URL:', API_BASE_URL);
console.log('✅ Full health check URL:', `${API_BASE_URL}/health`);

// DOM Elements
const elements = {
    // Status
    apiStatus: document.getElementById('apiStatus'),

    // Track List
    trackList: document.getElementById('trackList'),
    guideCard: document.getElementById('guideCard'),
    sidebarTitleCount: document.getElementById('sidebarTitleCount'),

    // Screen Reader Announcements
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

    // Process Card (shown after upload)
    processCard: document.getElementById('processCard'),
    cancelUploadBtn: document.getElementById('cancelUploadBtn'),
    confirmUploadBtn: document.getElementById('confirmUploadBtn'),

    // YouTube Download
    youtubeUrl: document.getElementById('youtubeUrl'),
    youtubeName: document.getElementById('youtubeName'),
    downloadYoutubeBtn: document.getElementById('downloadYoutubeBtn'),
    youtubeProgress: document.getElementById('youtubeProgress'),
    youtubeProgressText: document.getElementById('youtubeProgressText'),
    youtubeProgressPercent: document.getElementById('youtubeProgressPercent'),

    // Player Controls
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

    // Unified now-playing content area (replaces previewInfo, nowPlaying, processingProgress)
    nowPlayingContent: document.getElementById('nowPlayingContent'),
    nowPlayingHeader: document.getElementById('nowPlayingHeader'),
    bpmBadge: document.getElementById('bpmBadge'),
    bpmValue: document.querySelector('.bpm-value'),
    vizMode: document.getElementById('vizMode'),

    // Analysis Card
    analysisCard: document.getElementById('analysisCard'),
    statBpm: document.getElementById('statBpm'),
    statStyle: document.getElementById('statStyle'),
    statMood: document.getElementById('statMood'),
    statEnergy: document.getElementById('statEnergy'),
    statKey: document.getElementById('statKey'),

    // Waveform
    waveform: document.getElementById('waveform'),

    // Audio Elements
    audioPlayer: document.getElementById('audioPlayer'),

    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage'),
};

// State
let state = {
    tracks: [],
    // currentTrack removed - use selectedTracks array instead for multi-select
    selectedTracks: [],  // Array of {track, index, volume} for multi-track playback
    isPlaying: false,
    isLooping: false,
    apiConnected: false,
    uploadVisible: false,
    selectedFile: null,  // DEPRECATED: Use uploadedFile instead
    audioContext: null,
    analyser: null,
    trackVolumes: {},  // NEW: Map track name -> volume (0-100)
    pendingSeekPosition: null,  // NEW: Store seek position before playback starts (0-100 percentage)
    storedSeekTime: null,  // NEW: Store actual seek time in seconds for syncing later audio elements
    isUploading: false,  // NEW: Track upload state to prevent mid-upload panel closure
    originalFilePosition: 0,  // NEW: Track position of original file independently of audio element

    // NEW: Unified uploaded file state (replaces selectedFile for file tracking)
    uploadedFile: {
        name: null,           // File name (e.g., "song.mp3")
        path: null,           // Relative path (e.g., "storage/uploaded/song.mp3")
        size: null,           // File size in bytes
        duration: null,       // Duration in seconds
        source: null,         // Origin of the file: 'upload' | 'youtube'
        timestamp: null,      // When file was uploaded/downloaded (ms since epoch)
        isSeparated: false,   // Whether separation has been run
    },

    // NEW: Processing state
    processing: false,           // Currently processing (upload/download/separation)
    processingType: null,        // Type: 'upload' | 'download' | 'separation'
};

// Canvas Context
let waveformCtx = null;
let animationId = null;

/**
 * Initialize the Application
 */
async function init() {
    console.log('Initializing Drum Trainer Web App...');

    // Setup waveform canvas context
    if (elements.waveform) {
        waveformCtx = elements.waveform.getContext('2d');
        resizeWaveformCanvas();
        window.addEventListener('resize', resizeWaveformCanvas);
    }

    // Setup event listeners
    setupEventListeners();
    setupKeyboardShortcuts();

    // Check API connection
    const connected = await checkApiConnection();
    if (connected) {
        await loadTracks();
    } else {
        showConnectionHelp();
    }
}

/**
 * Resize waveform canvas to match container
 */
function resizeWaveformCanvas() {
    if (!elements.waveform || !elements.waveform.parentElement) return;

    const container = elements.waveform.parentElement;
    const rect = container.getBoundingClientRect();

    elements.waveform.width = rect.width;
    elements.waveform.height = rect.height;

    // Draw initial state
    if (waveformCtx) {
        drawEmptyWaveform();
    }
}

/**
 * Show connection help
 */
function showConnectionHelp() {
    elements.trackList.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">⚠️</div>
            <h3>无法连接到 API</h3>
            <p>请确保 FastAPI 服务器正在运行</p>
            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;">
                在终端运行：<br>
                <code style="background: var(--bg-tertiary); padding: 4px 8px; border-radius: 4px; display: inline-block; margin-top: 4px;">
                    uv run uvicorn api.server:app --host 0.0.0.0 --port 8000
                </code>
            </p>
            <button id="retryConnectionBtn" class="btn-primary" style="margin-top: 1rem;">重试连接</button>
        </div>
    `;

    const retryBtn = document.getElementById('retryConnectionBtn');
    if (retryBtn) {
        retryBtn.addEventListener('click', async () => {
            await checkApiConnection();
            if (state.apiConnected) {
                await loadTracks();
            }
        });
    }
}

/**
 * Setup Event Listeners
 */
function setupEventListeners() {
    // Refresh buttons
    if (elements.refreshBtn) {
        elements.refreshBtn.addEventListener('click', () => {
            if (state.apiConnected) {
                loadTracks();
                showToast('刷新音轨列表', 'success');
            } else {
                showToast('API 未连接', 'error');
            }
        });
    }

    // Clear button
    if (elements.clearBtn) {
        elements.clearBtn.addEventListener('click', clearSelection);
    }

    if (elements.emptyRefreshBtn) {
        elements.emptyRefreshBtn.addEventListener('click', () => {
            if (state.apiConnected) {
                loadTracks();
                showToast('刷新音轨列表', 'success');
            }
        });
    }

    // Upload toggle
    if (elements.uploadBtn) {
        elements.uploadBtn.addEventListener('click', toggleUploadPanel);
    }

    // File selection
    if (elements.selectFileBtn) {
        elements.selectFileBtn.addEventListener('click', () => {
            elements.fileInput.click();
        });
    }

    if (elements.fileInput) {
        elements.fileInput.addEventListener('change', handleFileSelect);
    }

    // YouTube download
    if (elements.downloadYoutubeBtn) {
        elements.downloadYoutubeBtn.addEventListener('click', handleYouTubeDownload);
    }

    // File preview actions (Process/Cancel/Confirm/Clear button)
    if (elements.cancelUploadBtn) {
        elements.cancelUploadBtn.addEventListener('click', cancelFilePreview);
    }
    // Note: confirmUploadBtn is no longer used - Process button is now in now-playing card

    // Drag and drop
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
            if (files.length > 0) {
                handleFileSelect({ target: { files } });
            }
        });

        // Keyboard accessibility for dropzone (Enter or Space to open file picker)
        dropzone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (!dropzone.classList.contains('disabled') && elements.fileInput) {
                    elements.fileInput.click();
                }
            }
        });
    }

    // Player controls - Unified Play/Pause Toggle
    if (elements.playPauseBtn) {
        elements.playPauseBtn.addEventListener('click', togglePlayPause);
    }
    if (elements.stopBtn) {
        elements.stopBtn.addEventListener('click', stop);
    }

    // Seek bar - both input (drag) and change (click) events
    if (elements.seekBar) {
        elements.seekBar.addEventListener('input', (e) => {
            console.log('Seek bar INPUT event:', e.target.value);
            seek();
        });
        elements.seekBar.addEventListener('change', (e) => {
            console.log('Seek bar CHANGE event:', e.target.value);
            seek();
        });
        console.log('✅ Seek bar event listeners attached');
    }

    // Volume
    if (elements.volumeSlider) {
        elements.volumeSlider.addEventListener('input', (e) => {
            const value = e.target.value;
            if (elements.audioPlayer) {
                elements.audioPlayer.volume = value / 100;
            }
            elements.volumeValue.textContent = `${value}%`;
        });
    }

    // Speed
    if (elements.speedSlider) {
        elements.speedSlider.addEventListener('input', (e) => {
            const value = e.target.value;
            const speed = value / 100;
            if (elements.audioPlayer) {
                elements.audioPlayer.playbackRate = speed;
            }
            elements.speedValue.textContent = `${speed.toFixed(1)}x`;
        });
    }

    // Loop
    if (elements.loopCheckbox) {
        elements.loopCheckbox.addEventListener('change', (e) => {
            state.isLooping = e.target.checked;
            if (elements.audioPlayer) {
                elements.audioPlayer.loop = state.isLooping;
            }
        });
    }

    // Audio events - Note: Individual track audio elements are created dynamically
    // The main audioPlayer is for backward compatibility but new multi-track system
    // uses dynamically created audio elements per track
    if (elements.audioPlayer) {
        elements.audioPlayer.addEventListener('timeupdate', updateProgress);
        elements.audioPlayer.addEventListener('loadedmetadata', updateDuration);
        elements.audioPlayer.addEventListener('ended', handleTrackEnd);
        elements.audioPlayer.addEventListener('play', () => {
            state.isPlaying = true;
            updatePlayState();
            startRealtimeVisualization();
        });
        elements.audioPlayer.addEventListener('pause', () => {
            // Bug Fix #5: Only update state if it's currently playing (prevents race condition)
            if (state.isPlaying) {
                state.isPlaying = false;
                updatePlayState();
                stopRealtimeVisualization();
            }
        });
        elements.audioPlayer.addEventListener('error', (e) => {
            console.error('Audio error:', e);
            showToast('音频加载失败', 'error');
        });
    }
}

/**
 * Setup Keyboard Shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Don't trigger if typing in an input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

        switch (e.code) {
            case 'Space':
                e.preventDefault();
                // Use unified toggle logic for space bar
                togglePlayPause();
                break;
            case 'Escape':
                stop();
                break;
            case 'ArrowRight':
                if (state.selectedTracks.length > 0 && elements.audioPlayer) {
                    elements.audioPlayer.currentTime = Math.min(
                        elements.audioPlayer.currentTime + 5,
                        elements.audioPlayer.duration || 0
                    );
                }
                break;
            case 'ArrowLeft':
                if (state.selectedTracks.length > 0 && elements.audioPlayer) {
                    elements.audioPlayer.currentTime = Math.max(
                        elements.audioPlayer.currentTime - 5,
                        0
                    );
                }
                break;
            case 'KeyR':
                if (state.apiConnected) {
                    loadTracks();
                    showToast('刷新音轨列表', 'success');
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
}

/**
 * Check API Connection with Better Error Handling
 */
async function checkApiConnection() {
    console.log('🧪 Starting API connection check...');
    updateApiStatus('connecting', '连接中...');

    const healthUrl = `${API_BASE_URL}/health`;
    console.log('📡 Fetching from:', healthUrl);

    try {
        const response = await fetch(healthUrl, {
            method: 'GET',
            mode: 'cors',
            signal: AbortSignal.timeout(5000),
            cache: 'no-cache',
        });

        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);

        if (response.ok) {
            const data = await response.json();
            state.apiConnected = true;
            updateApiStatus('connected', `已连接 (${data.device.toUpperCase()})`);
            // Enable player controls now that API is connected
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

        // Provide helpful feedback
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            console.error('💡 Likely cause: CORS or network issue');
        }
        if (error.name === 'AbortError') {
            console.error('💡 Likely cause: Server not responding or timeout');
        }
    }

    state.apiConnected = false;
    updateApiStatus('disconnected', '未连接');
    return false;
}

/**
 * Update API Status Indicator
 */
function updateApiStatus(status, text) {
    if (!elements.apiStatus) return;

    elements.apiStatus.className = `status-badge ${status}`;
    const statusText = elements.apiStatus.querySelector('.status-text');
    if (statusText) {
        statusText.textContent = text;
    }
}

/**
 * Show skeleton loading state for track list
 */
function showTrackSkeletonLoading(count = 3) {
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
    elements.trackList.innerHTML = skeletons.join('');
}

/**
 * Load Tracks from API
 * @param {Object} options - Options for loading tracks
 * @param {boolean} options.showAddedMessage - Show toast indicating tracks were added
 */
async function loadTracks(options = {}) {
    if (!state.apiConnected) {
        showToast('API 未连接', 'error');
        showConnectionHelp();
        return;
    }

    // Show skeleton loading state
    showTrackSkeletonLoading(3);

    try {
        console.log('Fetching tracks from:', `${API_BASE_URL}/tracks/list`);

        // Add timestamp to prevent browser caching
        const url = `${API_BASE_URL}/tracks/list?t=${Date.now()}`;
        console.log('Request URL with cache-busting:', url);

        const response = await fetch(url, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
            }
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', Object.fromEntries(response.headers.entries()));

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Received tracks:', data);
        console.log('Track count:', data.length);

        state.tracks = data;

        if (!data || data.length === 0) {
            console.log('No tracks found - showing empty state');
            elements.trackList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎵</div>
                    <h3>暂无音轨</h3>
                    <p>点击右上角 + 按钮上传音频文件</p>
                    <p class="guide-subtext">💡 上传后可直接播放，或点击"处理"分离鼓声</p>
                </div>
            `;
            // Show upload panel if no tracks exist
            if (elements.uploadPanel) {
                elements.uploadPanel.classList.remove('hidden');
                if (elements.uploadBtn) {
                    elements.uploadBtn.disabled = false;
                    elements.uploadBtn.textContent = '+ 上传';
                }
                state.uploadVisible = true;
                state.uploadLocked = false;
            }
            // Hide guide card and reset title count
            if (elements.guideCard) {
                elements.guideCard.classList.add('hidden');
            }
            updateSidebarTitleCount(0);
            return;
        }

        renderTrackList(data);
        // Enable player controls
        enablePlayerControls(true);

        // Fold upload panel if tracks already exist
        // This makes sense when page loads and tracks are already separated
        if (elements.uploadPanel) {
            elements.uploadPanel.classList.add('hidden');
            state.uploadVisible = false;
            state.uploadLocked = true;
            if (elements.uploadBtn) {
                elements.uploadBtn.disabled = true;
                elements.uploadBtn.textContent = '已处理';
            }
        }

        // Find and set the original (non-separated) file for song info bar
        // This ensures the song info bar persists after page reload
        const originalFile = data.find(track => !track.is_separated);
        if (originalFile) {
            state.selectedFile = {
                name: originalFile.name,
                path: originalFile.path,
                size: originalFile.size,
                duration: originalFile.duration,
                source: originalFile.source || 'upload',
                isSeparated: false,
            };
            console.log('Found original file for song info bar:', originalFile.name);
        }

        // Bug Fix #4: Show context-specific message
        if (options.showAddedMessage) {
            showToast(`✅ 成功加载 ${data.length} 个音轨`, 'success');
        } else {
            showToast(`成功加载 ${data.length} 个音轨`, 'success');
        }

        // Update now-playing display to show song info bar if we have an original file
        if (state.selectedFile) {
            updateNowPlayingDisplay();
            // Also update the total time display with the original file's duration
            if (elements.totalTime && state.selectedFile.duration) {
                elements.totalTime.textContent = formatTime(state.selectedFile.duration);
            }
        }

    } catch (error) {
        console.error('Error loading tracks:', error);
        elements.trackList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <h3>加载失败</h3>
                <p>${error.message}</p>
                <button id="retryBtn" class="btn-secondary">重试</button>
            </div>
        `;

        const retryBtn = document.getElementById('retryBtn');
        if (retryBtn) {
            retryBtn.addEventListener('click', loadTracks);
        }

        showToast(`加载失败: ${error.message}`, 'error');
    }
}

/**
 * Render Track List with click-to-select
 * Only shows separated tracks (original file is not displayed in the track list)
 */
function renderTrackList(tracks) {
    // Filter to show ONLY separated tracks in the track list
    // Original file is available for playback but not shown in the track list
    const separatedTracks = tracks.filter(track => track.is_separated);
    const hasSeparatedTracks = separatedTracks.length > 0;

    // Update sidebar title count
    updateSidebarTitleCount(hasSeparatedTracks ? separatedTracks.length : 0);

    // Show/hide guide card based on whether we have separated tracks
    if (elements.guideCard) {
        if (hasSeparatedTracks) {
            elements.guideCard.classList.remove('hidden');
        } else {
            elements.guideCard.classList.add('hidden');
        }
    }

    // If no separated tracks, show a special message explaining the workflow
    if (!hasSeparatedTracks) {
        // Find the original file to show context
        const originalFile = tracks.find(track => !track.is_separated);
        if (originalFile) {
            elements.trackList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎵</div>
                    <h3>原始文件已就绪</h3>
                    <p class="filename">${originalFile.name}</p>
                    <p class="guide-subtext">💡 <strong>播放完整歌曲</strong> - 点击播放按钮直接播放</p>
                    <p class="guide-subtext">💡 <strong>分离音轨</strong> - 使用上方"文件预览"中的"开始分离"按钮</p>
                </div>
            `;
        } else {
            // Shouldn't happen, but fallback
            elements.trackList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎵</div>
                    <h3>等待处理</h3>
                    <p>上传的文件准备就绪</p>
                </div>
            `;
        }
        return;
    }

    // Render separated tracks
    elements.trackList.innerHTML = '';

    separatedTracks.forEach((track, index) => {
        const trackCard = document.createElement('div');

        // Get track type info for styling
        const trackInfo = getTrackIconInfo(track.name);

        // Build base classes with type-specific styling
        let cardClasses = `track-card fade-in ${trackInfo.class}`;
        trackCard.className = cardClasses;
        trackCard.style.animationDelay = `${index * 0.05}s`;
        trackCard.dataset.index = index;
        trackCard.dataset.type = trackInfo.class;

        // Check if this track is currently selected (in selectedTracks array)
        const isSelected = state.selectedTracks.some(t => t.track.name === track.name);
        if (isSelected) {
            trackCard.classList.add('active');
        }

        const duration = formatTime(track.duration);
        const sizeMB = (track.size / (1024 * 1024)).toFixed(1);

        // Use the icon from track info
        const icon = trackInfo.icon;

        // Get stored volume or default to 50
        const storedVolume = state.trackVolumes[track.name] ?? 50;

        trackCard.innerHTML = `
            <div class="track-icon">${icon}</div>
            <div class="track-info">
                <div class="track-name">${track.name}</div>
                <div class="track-meta">
                    <span>⏱️ ${duration}</span>
                    <span>💾 ${sizeMB} MB</span>
                    <span>🎵 ${track.channels === 2 ? '立体声' : '单声道'}</span>
                    <span> Hz ${track.samplerate}</span>
                </div>
            </div>
            <div class="track-actions">
                <button class="btn-glow" data-action="analyze" title="分析">📊</button>
                <div class="track-volume-container">
                    <input type="range"
                           class="track-volume-slider"
                           min="0" max="100" value="${storedVolume}"
                           data-track="${track.name}"
                           data-index="${index}"
                           orient="vertical"
                           title="音量">
                </div>
            </div>
        `;

        // Setup track card event listeners
        setupTrackCardListeners(trackCard, track, index);

        elements.trackList.appendChild(trackCard);
    });
}

/**
 * Update sidebar title count indicator
 * Shows track count when separated tracks exist
 */
function updateSidebarTitleCount(count) {
    if (!elements.sidebarTitleCount) return;

    if (count > 0) {
        elements.sidebarTitleCount.textContent = `${count} 分离`;
        elements.sidebarTitleCount.classList.remove('hidden');
        elements.sidebarTitleCount.classList.add('visible');
    } else {
        elements.sidebarTitleCount.classList.add('hidden');
        elements.sidebarTitleCount.classList.remove('visible');
    }
}

/**
 * Setup Track Card Event Listeners
 */
function setupTrackCardListeners(trackCard, track, index) {
    // Track selection - single click to toggle (add/remove from selection)
    trackCard.addEventListener('click', (e) => {
        // Don't trigger if clicking on analyze button or volume slider
        if (e.target.closest('button[data-action="analyze"]') ||
            e.target.closest('.track-volume-slider')) {
            return;
        }

        // Check if track is currently selected
        const isSelected = state.selectedTracks.some(t => t.track.name === track.name);

        if (isSelected) {
            // Track is selected - remove from selection (toggle off)
            removeFromSelectedTracks(index);
        } else {
            // Track is not selected - add to selection (toggle on)
            addToSelectedTracks(track, index);
        }
    });

    // Analyze button - does not affect selection
    const analyzeBtn = trackCard.querySelector('button[data-action="analyze"]');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            analyzeTrack(track);
        });
    }

    // Volume slider for individual track - does not affect selection
    const volumeSlider = trackCard.querySelector('.track-volume-slider');
    if (volumeSlider) {
        volumeSlider.addEventListener('click', (e) => {
            e.stopPropagation();  // Don't trigger card selection
        });

        volumeSlider.addEventListener('input', (e) => {
            e.stopPropagation();
            const trackName = e.target.dataset.track;
            const volume = parseInt(e.target.value);
            state.trackVolumes[trackName] = volume;

            // Bug Fix #2: Also update selectedTracks if this track is currently selected
            const selectedTrack = state.selectedTracks.find(t => t.track.name === trackName);
            if (selectedTrack) {
                selectedTrack.volume = volume;
            }

            // If this track is currently playing, adjust its volume IMMEDIATELY (no stop)
            const audioElement = document.querySelector(`audio[data-track="${trackName}"]`);
            if (audioElement) {
                audioElement.volume = volume / 100;
            }

            console.log(`Volume for ${trackName}: ${volume}%`);
        });
    }
}

/**
 * Add track to selected tracks (multi-select support)
 */
function addToSelectedTracks(track, index) {
    // Check if already in selection
    if (state.selectedTracks.some(t => t.track.name === track.name)) {
        return;
    }

    // Bug Fix #1: Initialize volume in state if not exists
    if (state.trackVolumes[track.name] === undefined) {
        state.trackVolumes[track.name] = 50;
    }

    // Add to selection array
    state.selectedTracks.push({
        track: track,
        index: index,
        volume: state.trackVolumes[track.name]
    });

    // Update UI - add green border
    const card = document.querySelector(`[data-index="${index}"]`);
    if (card) card.classList.add('active');

    // Update total time display
    updateTotalTimeForSelectedTracks();

    // Update now-playing display
    updateNowPlayingDisplay();

    // If currently playing, start this track immediately (non-stop, synced)
    if (state.isPlaying) {
        // Check if the original file is currently playing
        // If so, we need to stop it first before starting the separated track
        // This prevents the original (full mix) and separated track from playing simultaneously
        const originalIsPlaying = window.originalAudioPlayer && !window.originalAudioPlayer.paused;

        // Determine the target position before stopping anything
        let targetPosition = null;
        if (originalIsPlaying) {
            targetPosition = window.originalAudioPlayer.currentTime;
            console.log('Original file is playing at position:', targetPosition);
            console.log('Stopping original, will start separated track from same position');

            // Stop the original BEFORE playing the new track
            window.originalAudioPlayer.pause();
            window.originalAudioPlayer.currentTime = 0;
        }

        // Get current position from existing separated tracks (or use saved position from original)
        if (targetPosition === null) {
            targetPosition = getCurrentPlaybackPosition();
        }

        console.log(`Adding track ${track.name} during playback, syncing to position: ${targetPosition}s`);

        // Play the track with the determined position
        playTrackImmediately(track, targetPosition);

        // Clear stored seek time since we've used it
        state.storedSeekTime = null;

        // Additional sync after a short delay to ensure all tracks are synced
        setTimeout(() => {
            if (state.isPlaying) {
                syncAllAudio();
            }
        }, 100);
    }

    showToast(`已添加: ${track.name}`, 'success');
}

/**
 * Remove track from selected tracks (multi-select support)
 */
function removeFromSelectedTracks(index) {
    // Find the track to remove
    const trackToRemove = state.selectedTracks.find(t => t.index === index);
    if (!trackToRemove) return;

    // Remove from selection array
    state.selectedTracks = state.selectedTracks.filter(t => t.index !== index);

    // Update UI - remove green border
    const card = document.querySelector(`[data-index="${index}"]`);
    if (card) card.classList.remove('active');

    // Update total time display (or show original file duration if no tracks left)
    if (state.selectedTracks.length === 0) {
        // Show original file duration if available
        if (state.selectedFile && state.selectedFile.duration) {
            if (elements.totalTime) elements.totalTime.textContent = formatTime(state.selectedFile.duration);
        } else if (window.originalAudioPlayer && window.originalAudioPlayer.duration) {
            if (elements.totalTime) elements.totalTime.textContent = formatTime(window.originalAudioPlayer.duration);
        } else {
            if (elements.totalTime) elements.totalTime.textContent = '0:00';
        }
    } else {
        updateTotalTimeForSelectedTracks();
    }

    // Update now-playing display
    updateNowPlayingDisplay();

    // If currently playing OR paused, remove this audio element to keep state consistent
    // This ensures that when user clicks Play after deselecting a track while paused,
    // the remaining audio elements match the current selection
    const audioElement = document.querySelector(`audio[data-track="${trackToRemove.track.name}"]`);
    if (audioElement) {
        // Before removing, save the current position if we're paused and this is the only/last track being removed
        // This allows position to be preserved when switching tracks
        if (audioElement.paused && audioElement.currentTime > 0) {
            const hadNonZeroTime = audioElement.currentTime;
            console.log(`Saving position ${hadNonZeroTime}s from deselected track ${trackToRemove.track.name}`);
            state.storedSeekTime = hadNonZeroTime;
        }

        audioElement.pause();
        audioElement.remove();
    }

    showToast(`已移除: ${trackToRemove.track.name}`, 'info');
}

/**
 * Clear all selected tracks and delete uploaded files
 * Deletes storage/uploaded/ directory and resets UI
 * Uses uploadedFile as the source of truth for file management
 */
async function clearSelection() {
    console.log('=== clearSelection() called ===');
    console.log('Currently selected tracks:', state.selectedTracks.map(t => t.track.name));

    // Stop all audio if playing
    if (state.isPlaying) {
        stopAllAudio();
    }

    // Call API to clear storage/uploaded/ directory
    if (state.apiConnected) {
        try {
            const response = await fetch(`${API_BASE_URL}/separation/clear`, {
                method: 'POST',
            });

            if (response.ok) {
                showToast('已清除所有上传文件', 'success');
            } else {
                showToast('清除失败', 'error');
            }
        } catch (error) {
            console.error('Clear error:', error);
            showToast(`清除失败: ${error.message}`, 'error');
        }
    }

    // Clear UI highlights for all selected tracks
    state.selectedTracks.forEach(selected => {
        const card = document.querySelector(`[data-index="${selected.index}"]`);
        if (card) card.classList.remove('active');
    });

    // Clear the selection array
    state.selectedTracks = [];

    // Reset state
    state.uploadLocked = false;
    state.selectedFile = null;
    state.uploadedFile = { name: null, path: null, size: null, duration: null, source: null, timestamp: null, isSeparated: false };

    // Clear processing state
    state.processing = false;
    state.processingType = null;

    // Clear seek-related state
    state.pendingSeekPosition = null;
    state.storedSeekTime = null;

    // Clear trackList UI - show empty state
    if (elements.trackList) {
        elements.trackList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🎵</div>
                <h3>暂无音轨</h3>
                <p>点击右上角 + 按钮上传音频文件</p>
                <button id="emptyRefreshBtn" class="btn-secondary">刷新</button>
            </div>
        `;

        // Re-attach event listener for refresh button
        const emptyRefreshBtn = document.getElementById('emptyRefreshBtn');
        if (emptyRefreshBtn) {
            emptyRefreshBtn.addEventListener('click', () => {
                if (state.apiConnected) {
                    loadTracks();
                    showToast('刷新音轨列表', 'success');
                }
            });
        }
    }

    // Hide guide card and reset title count
    if (elements.guideCard) {
        elements.guideCard.classList.add('hidden');
    }
    updateSidebarTitleCount(0);

    // Reset UI elements
    if (elements.totalTime) elements.totalTime.textContent = '0:00';
    if (elements.seekBar) elements.seekBar.value = 0;
    if (elements.currentTime) elements.currentTime.textContent = '0:00';
    if (elements.nowPlayingContent) {
        elements.nowPlayingContent.innerHTML = '<div class="placeholder-text">选择音轨开始播放</div>';
    }

    // Stop any ongoing visualization
    stopRealtimeVisualization();

    // Reset upload panel UI - UNFOLD and unlock
    elements.uploadPanel.classList.remove('hidden');
    if (elements.uploadBtn) {
        elements.uploadBtn.disabled = false;
        elements.uploadBtn.textContent = '+ 上传';
    }
    state.uploadVisible = true;
    state.uploadLocked = false;

    // Clear preview from now-playing-card
    clearPreviewFromNowPlayingCard();

    // Reset file input
    if (elements.fileInput) {
        elements.fileInput.value = '';
    }

    // Hide progress bar
    if (elements.uploadProgress) {
        elements.uploadProgress.classList.add('hidden');
    }

    // Show upload dropzone (upload area)
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) uploadDropzone.classList.remove('hidden');

    // Hide process card
    if (elements.processCard) {
        elements.processCard.classList.add('hidden');
    }

    // Remove processing state from upload panel
    if (elements.uploadPanel) {
        elements.uploadPanel.classList.remove('processing');
    }

    // Reset the Process button back to initial state
    resetProcessButton();

    // Update play state
    updatePlayState();
}

/**
 * Get track type icon and color class based on track name
 */
function getTrackIconInfo(trackName) {
    const name = trackName.toLowerCase();

    if (name.includes('drum')) {
        return { icon: '🥁', class: 'drum', displayName: 'Drums' };
    } else if (name.includes('bass')) {
        return { icon: '🎸', class: 'bass', displayName: 'Bass' };
    } else if (name.includes('vocal')) {
        return { icon: '🎤', class: 'vocals', displayName: 'Vocals' };
    } else if (name.includes('piano')) {
        return { icon: '🎹', class: 'piano', displayName: 'Piano' };
    } else if (name.includes('guitar')) {
        return { icon: '🎸', class: 'guitar', displayName: 'Guitar' };
    } else if (name.includes('other')) {
        return { icon: '🎵', class: 'other', displayName: 'Other' };
    } else {
        return { icon: '🎶', class: 'other', displayName: 'Track' };
    }
}

/**
 * Update the selected tracks info display with iconic representation
 */
function updateSelectedTracksInfo() {
    if (!elements.selectedTracksInfo || !elements.selectedTracksList) return;

    if (state.selectedTracks.length > 0) {
        elements.selectedTracksInfo.classList.remove('hidden');

        // Create iconic badges for each track (interactive with remove button)
        const badges = state.selectedTracks.map((t, index) => {
            const info = getTrackIconInfo(t.track.name);
            const duration = formatTime(t.track.duration);

            return `
                <span class="track-icon-badge ${info.class} interactive" data-track-index="${index}" title="${t.track.name} (${duration})">
                    <span class="icon">${info.icon}</span>
                    <span class="name">${info.displayName}</span>
                    <span class="remove" onclick="event.stopPropagation(); removeFromSelectedTracks(${index})">×</span>
                </span>
            `;
        }).join('');

        elements.selectedTracksList.innerHTML = badges;

        // Update the label to indicate these are selected tracks being played
        const label = elements.selectedTracksInfo.querySelector('.info-label');
        if (label) {
            label.textContent = '🎵 播放列表:';
        }
    } else {
        elements.selectedTracksInfo.classList.add('hidden');
    }
}

/**
 * Get current synchronized playback position (from any playing audio)
 */
function getCurrentPlaybackPosition() {
    const allAudio = document.querySelectorAll('audio[data-track]');
    console.log('getCurrentPlaybackPosition - found audio elements:', allAudio.length);

    // First, try to find a playing audio element with valid duration
    for (const audio of allAudio) {
        console.log(`  Audio ${audio.dataset.track}: paused=${audio.paused}, currentTime=${audio.currentTime}, duration=${audio.duration}`);
        if (!audio.paused && audio.currentTime > 0 && audio.duration && !isNaN(audio.duration)) {
            console.log(`  Using ${audio.dataset.track} as reference at ${audio.currentTime}s`);
            return audio.currentTime;
        }
    }

    // Fallback: find any audio element with valid currentTime (paused but positioned)
    for (const audio of allAudio) {
        if (audio.currentTime > 0 && audio.duration && !isNaN(audio.duration)) {
            console.log(`  Using paused audio ${audio.dataset.track} as reference at ${audio.currentTime}s`);
            return audio.currentTime;
        }
    }

    // Last resort: use pending seek time or stored seek time
    if (state.storedSeekTime) {
        console.log('  Using stored seek time:', state.storedSeekTime);
        return state.storedSeekTime;
    }

    console.log('  No suitable audio found, returning 0');
    return 0;
}

/**
 * Play a single track immediately without stopping other tracks
 * Used for non-stop playback when adding tracks during playback
 * @param {object} track - The track object to play
 * @param {boolean|number} syncPosition - If true, sync to current playback position. If a number, use that position.
 */
function playTrackImmediately(track, syncPosition = false) {
    console.log('=== playTrackImmediately() called ===');
    console.log('Track:', track.name, 'Sync position:', syncPosition);

    // Create or update audio element for this track
    let audioElement = document.querySelector(`audio[data-track="${track.name}"]`);
    console.log('Existing audio element found:', !!audioElement);

    if (!audioElement) {
        audioElement = document.createElement('audio');
        audioElement.dataset.track = track.name;
        audioElement.preload = 'auto';
        audioElement.style.display = 'none'; // Hidden audio element
        document.body.appendChild(audioElement);
        console.log('Created new audio element for:', track.name);

        // Connect to Web Audio API analyser for waveform visualization
        initAudioContext();
        connectAudioToAnalyser(audioElement);

        // Add event listeners for progress tracking and state updates (only add once for new elements)
        audioElement.addEventListener('timeupdate', updateProgress);
        audioElement.addEventListener('loadedmetadata', updateDuration);
        audioElement.addEventListener('ended', handleTrackEnd);
        audioElement.addEventListener('play', () => {
            // Update state when this audio element starts playing
            state.isPlaying = true;
            updatePlayState();
            startRealtimeVisualization();
        });
        audioElement.addEventListener('pause', () => {
            // Check if all audio elements are paused
            const allAudio = document.querySelectorAll('audio[data-track]');
            let allPaused = true;
            for (const audio of allAudio) {
                if (!audio.paused) {
                    allPaused = false;
                    break;
                }
            }
            // Bug Fix #5: Only update state if it's currently playing (prevents race condition)
            if (allPaused && state.isPlaying) {
                state.isPlaying = false;
                updatePlayState();
                stopRealtimeVisualization();
            }
        });
    }

    // Set source if not already set
    const audioUrl = `${API_BASE_URL}/tracks/audio/${track.name}`;
    if (audioElement.src !== audioUrl) {
        console.log('Setting audio source:', audioUrl);
        audioElement.src = audioUrl;
    } else {
        console.log('Audio source already set');
    }

    // Set volume from stored value
    const volume = state.trackVolumes[track.name] ?? 50;
    audioElement.volume = volume / 100;
    console.log('Set volume to:', volume);

    // Determine target time for sync
    let targetTime = 0;
    if (syncPosition === true) {
        // Boolean true: find current playback position from other audio elements
        targetTime = getCurrentPlaybackPosition();
        console.log('Syncing to current position:', targetTime);
    } else if (typeof syncPosition === 'number') {
        // Number: use the provided position directly
        targetTime = syncPosition;
        console.log('Syncing to provided position:', targetTime);
    }

    if (targetTime > 0) {
        audioElement.currentTime = targetTime;
    }

    // Play immediately
    console.log('Calling audioElement.play()...');
    audioElement.play().then(() => {
        console.log('Playback started successfully for:', track.name);
        console.log('Current time after play:', audioElement.currentTime);

        // After playback starts, ensure the position is correct (for better sync)
        if (syncPosition && targetTime > 0) {
            // Small delay to ensure audio is ready, then force sync
            setTimeout(() => {
                if (audioElement && Math.abs(audioElement.currentTime - targetTime) > 0.1) {
                    console.log('Correcting sync for:', track.name, 'from', audioElement.currentTime, 'to', targetTime);
                    audioElement.currentTime = targetTime;
                }
            }, 100);
        }
    }).catch(err => {
        console.error(`Error playing ${track.name}:`, err);
        console.error('Error name:', err.name);
        console.error('Error message:', err.message);
        showToast(`播放失败: ${track.name}`, 'error');

        // Bug Fix #4: Cleanup failed audio element and remove from selection
        if (audioElement && audioElement.parentNode) {
            audioElement.remove();
        }
        state.selectedTracks = state.selectedTracks.filter(t => t.track.name !== track.name);
    });
}

/**
 * Stop all audio elements (helper for non-stop playback)
 */
function stopAllAudio() {
    const allAudio = document.querySelectorAll('audio[data-track]');
    allAudio.forEach(audio => {
        audio.pause();
        audio.currentTime = 0;
        audio.remove();  // Remove audio element to allow fresh start on next play
    });

    // Also stop original audio player if exists
    if (window.originalAudioPlayer) {
        window.originalAudioPlayer.pause();
        window.originalAudioPlayer.currentTime = 0;
    }

    // Clear seek state when stopping all audio
    state.storedSeekTime = null;
    state.originalFilePosition = 0;  // Bug Fix #3: Clear original file position when stopping
}

/**
 * Pause all audio elements (helper for non-stop playback)
 */
function pauseAllAudio() {
    const allAudio = document.querySelectorAll('audio[data-track]');
    allAudio.forEach(audio => audio.pause());

    // Bug Fix #2: Also pause original audio player if it exists
    // The original audio player has dataset.track = 'original'
    if (window.originalAudioPlayer && !window.originalAudioPlayer.paused) {
        window.originalAudioPlayer.pause();
    }
}

/**
 * Enable/Disable Player Controls
 */
function enablePlayerControls(enabled) {
    const controls = [elements.playPauseBtn, elements.stopBtn, elements.seekBar];
    controls.forEach(control => {
        if (control) control.disabled = !enabled;
    });
}

/**
 * Analyze a Track
 */
async function analyzeTrack(track) {
    if (!state.apiConnected) {
        showToast('API 未连接', 'error');
        return;
    }

    showToast('正在分析...', 'info');

    try {
        // Fetch audio file
        const audioUrl = `${API_BASE_URL}/tracks/audio/${track.name}`;
        showToast('正在下载音频进行分析...', 'info');

        const audioResponse = await fetch(audioUrl);
        if (!audioResponse.ok) throw new Error('无法下载音频文件');
        const audioBlob = await audioResponse.blob();

        // Create FormData
        const formData = new FormData();
        const audioFile = new File([audioBlob], track.name, { type: 'audio/wav' });
        formData.append('file', audioFile);

        // Send to analysis endpoint
        const analyzeResponse = await fetch(`${API_BASE_URL}/analysis/analyze`, {
            method: 'POST',
            body: formData,
        });

        if (!analyzeResponse.ok) {
            throw new Error(`HTTP ${analyzeResponse.status}`);
        }

        const result = await analyzeResponse.json();

        if (result.status === 'success') {
            const analysis = result.analysis;

            // Show analysis card
            elements.analysisCard.classList.remove('hidden');

            // Update stat values
            elements.statBpm.textContent = analysis.bpm;
            elements.statStyle.textContent = analysis.style;
            elements.statMood.textContent = analysis.mood;
            elements.statEnergy.textContent = `${(analysis.energy * 100).toFixed(0)}%`;
            elements.statKey.textContent = analysis.key;

            // Update BPM badge
            elements.bpmValue.textContent = analysis.bpm;
            elements.bpmBadge.classList.remove('hidden');

            showToast(
                `✅ 分析完成: ${analysis.bpm} BPM | ${analysis.style} | ${analysis.mood}`,
                'success'
            );
        } else {
            showToast('分析失败', 'error');
        }

    } catch (error) {
        console.error('Analysis error:', error);
        showToast(`分析失败: ${error.message}`, 'error');
    }
}

/**
 * Play - Multi-track playback support
 */
function play() {
    console.log('=== play() called ===');
    console.log('Selected tracks:', state.selectedTracks.map(t => t.track.name));
    console.log('Is already playing:', state.isPlaying);
    console.log('Pending seek position:', state.pendingSeekPosition);

    // Check if we should resume instead of starting fresh
    // If there are existing audio elements and we're not currently playing, resume
    const existingAudio = document.querySelectorAll('audio[data-track]');
    if (!state.isPlaying && existingAudio.length > 0) {
        // Check if the existing audio elements match the current selection
        const existingTrackNames = Array.from(existingAudio).map(a => a.dataset.track);
        const selectedTrackNames = state.selectedTracks.map(t => t.track.name);

        // Sort both arrays for comparison
        const existingSorted = [...existingTrackNames].sort();
        const selectedSorted = [...selectedTrackNames].sort();

        const matches = existingSorted.length === selectedSorted.length &&
                        existingSorted.every((name, i) => name === selectedSorted[i]);

        if (matches) {
            console.log('Found matching existing audio elements, using resume()');
            resume();
            return;
        } else {
            console.log('Existing audio elements don\'t match selection, stopping and recreating');
            console.log('  Existing:', existingSorted);
            console.log('  Selected:', selectedSorted);
            stopAllAudio();
            // Continue to create new audio elements
        }
    }

    // Check if we have selected separated tracks to play
    if (state.selectedTracks.length > 0) {
        console.log('Playing separated tracks');
        // Continue to the rest of the play function
    }
    // Check if we have an original file to play (when no tracks are selected)
    // This works whether separation has been done or not
    else if (state.selectedFile) {
        console.log('Playing original file (no tracks selected)');
        playOriginalFile();
        return;
    }
    // No tracks and no original file
    else {
        showToast('请先选择音轨', 'warning');
        return;
    }

    // Check if we need to establish API connection
    if (!state.apiConnected) {
        showToast('API 未连接', 'error');
        return;
    }

    // Stop and reset the original audio player if it exists
    // This prevents it from interfering with separated track playback
    if (window.originalAudioPlayer) {
        console.log('Pausing and resetting original audio player');
        window.originalAudioPlayer.pause();
        window.originalAudioPlayer.currentTime = 0;
        window.originalAudioPlayer.src = '';
    }

    // Track how many audio elements are ready
    let readyCount = 0;
    const totalNeeded = state.selectedTracks.length;
    const audioElements = [];
    const timeoutIds = []; // Track timeouts for cleanup

    // Apply pending seek position to all tracks once the first one is ready
    const applySeekIfNeeded = () => {
        console.log('=== applySeekIfNeeded() called ===');
        console.log('Pending seek position:', state.pendingSeekPosition);
        console.log('Stored seek time:', state.storedSeekTime);
        console.log('Audio elements count:', audioElements.length);

        // Check if we need to apply stored seek time (from track switch or pending seek)
        if ((state.pendingSeekPosition !== null || state.storedSeekTime !== null) && audioElements.length > 0) {
            // Debug: log all audio element states
            audioElements.forEach((audio, i) => {
                console.log(`  Audio ${i} (${audio.dataset.track}): duration=${audio.duration}, isNaN=${isNaN(audio.duration)}`);
            });

            // Use the first audio element with a valid duration
            const referenceAudio = audioElements.find(a => a.duration && !isNaN(a.duration));
            console.log('Reference audio:', referenceAudio ? referenceAudio.dataset.track : 'null');

            if (referenceAudio) {
                let seekTime = state.storedSeekTime;

                // If we have a pending seek position (from seek bar), calculate seek time from percentage
                if (state.pendingSeekPosition !== null) {
                    seekTime = (state.pendingSeekPosition / 100) * referenceAudio.duration;
                    console.log('Calculated seek time from pending position:', state.pendingSeekPosition, '% ->', seekTime, 's');
                }

                if (seekTime !== null && seekTime !== undefined) {
                    console.log('Applying seek time:', seekTime, 's');

                    // Store seekTime for future audio elements that haven't loaded yet
                    // This is crucial for multi-track sync
                    state.storedSeekTime = seekTime;
                    console.log('Stored seekTime for future elements:', seekTime);

                    audioElements.forEach(audio => {
                        if (audio.duration && !isNaN(audio.duration)) {
                            console.log(`  Setting ${audio.dataset.track} currentTime to ${seekTime}`);
                            audio.currentTime = seekTime;
                        }
                    });
                    // Only clear pending position AFTER all elements have been seeked
                    // Check if all audio elements now have valid durations (meaning all have been processed)
                    const allHaveDurations = audioElements.every(a => a.duration && !isNaN(a.duration));
                    if (allHaveDurations) {
                        state.pendingSeekPosition = null;
                        state.storedSeekTime = null;
                        console.log('Pending seek position and stored seek time cleared (all elements processed)');
                    } else {
                        console.log('Seek position NOT cleared yet (some elements still loading)');
                    }
                } else {
                    console.log('No valid seek time to apply');
                }
            } else {
                console.log('No reference audio found yet - cannot apply seek');
            }
        } else {
            console.log('Not applying seek: pendingSeekPosition=', state.pendingSeekPosition, 'storedSeekTime=', state.storedSeekTime, 'audioElements.length=', audioElements.length);
        }
    };

    // Function to check if all elements are ready and start playback
    const checkAllReadyAndStart = () => {
        console.log('=== checkAllReadyAndStart() called ===');
        console.log(`Ready count: ${readyCount}, Total needed: ${totalNeeded}`);

        // Check if all elements have valid durations
        const allReady = audioElements.every(a => a.duration && !isNaN(a.duration));
        console.log('All elements have valid duration:', allReady);

        if (allReady) {
            console.log('All tracks ready - starting playback in 50ms');
            applySeekIfNeeded(); // Apply seek one more time just in case
            setTimeout(() => startPlayback(audioElements), 50);
        }
    };

    // Preload all audio elements first (for better sync)
    state.selectedTracks.forEach(selected => {
        console.log('Preparing audio for:', selected.track.name);

        let audioElement = document.querySelector(`audio[data-track="${selected.track.name}"]`);
        console.log('  Existing audio element:', !!audioElement);

        if (!audioElement) {
            audioElement = document.createElement('audio');
            audioElement.dataset.track = selected.track.name;
            audioElement.preload = 'auto';
            audioElement.style.display = 'none';
            document.body.appendChild(audioElement);
            console.log('  Created new audio element');

            // Connect to Web Audio API analyser for waveform visualization
            initAudioContext();
            connectAudioToAnalyser(audioElement);
        }

        // Set up event listeners BEFORE setting src to catch loadedmetadata
        audioElement.addEventListener('timeupdate', updateProgress);
        audioElement.addEventListener('ended', handleTrackEnd);
        audioElement.addEventListener('play', () => {
            // Update state when this audio element starts playing
            state.isPlaying = true;
            updatePlayState();
            startRealtimeVisualization();
        });
        audioElement.addEventListener('pause', () => {
            // Check if all audio elements are paused
            const allAudio = document.querySelectorAll('audio[data-track]');
            let allPaused = true;
            for (const audio of allAudio) {
                if (!audio.paused) {
                    allPaused = false;
                    break;
                }
            }
            // Bug Fix #5: Only update state if it's currently playing (prevents race condition)
            if (allPaused && state.isPlaying) {
                state.isPlaying = false;
                updatePlayState();
                stopRealtimeVisualization();
            }
        });

        // Track if this element has already loaded metadata for this src
        let hasLoadedMetadata = false;

        // Use once to avoid multiple listeners on src changes
        const onMetadataLoaded = () => {
            if (hasLoadedMetadata) return; // Prevent duplicate calls
            hasLoadedMetadata = true;

            console.log(`  ${selected.track.name} metadata loaded, duration:`, audioElement.duration);
            readyCount++;

            // If there's a stored seek time (from another track that loaded first), apply it to this track too
            if (state.storedSeekTime !== null && state.storedSeekTime !== undefined) {
                console.log(`  Applying stored seekTime (${state.storedSeekTime}s) to ${selected.track.name}`);
                audioElement.currentTime = state.storedSeekTime;
            }

            applySeekIfNeeded(); // Try to apply seek now
            checkAllReadyAndStart(); // Check if we can start
        };

        // Remove existing loadedmetadata listeners to avoid duplicates
        audioElement.removeEventListener('loadedmetadata', updateDuration);
        audioElement.addEventListener('loadedmetadata', updateDuration);

        // Use a separate listener for the initial metadata load
        audioElement.addEventListener('loadedmetadata', onMetadataLoaded);

        const audioUrl = `${API_BASE_URL}/tracks/audio/${selected.track.name}`;
        console.log('  Setting src:', audioUrl);

        // Set currentTime to stored seek time if available, otherwise 0
        // This ensures position is preserved when switching tracks
        if (state.storedSeekTime !== null && state.storedSeekTime !== undefined) {
            console.log(`  Pre-setting currentTime to stored seek time: ${state.storedSeekTime}s`);
            audioElement.currentTime = state.storedSeekTime;
        } else {
            audioElement.currentTime = 0;
        }
        audioElement.src = audioUrl;

        audioElement.volume = (state.trackVolumes[selected.track.name] ?? 50) / 100;
        console.log('  Volume:', audioElement.volume);

        // Check immediately after setting src - sometimes metadata is already available
        // Use a small delay to let the browser process the src change
        const immediateCheck = () => {
            console.log(`  ${selected.track.name} immediate check: duration=${audioElement.duration}, readyState=${audioElement.readyState}`);
            // readyState: 0=HAVE_NOTHING, 1=HAVE_METADATA, 2=HAVE_CURRENT_DATA, 3=HAVE_FUTURE_DATA, 4=HAVE_ENOUGH_DATA
            if (audioElement.readyState >= 1 && audioElement.duration && !isNaN(audioElement.duration)) {
                console.log(`  ${selected.track.name} already has metadata, using duration: ${audioElement.duration}`);
                // Apply stored seek time if available
                if (state.storedSeekTime !== null && state.storedSeekTime !== undefined) {
                    console.log(`  Applying stored seekTime (${state.storedSeekTime}s) to ${selected.track.name}`);
                    audioElement.currentTime = state.storedSeekTime;
                }
                onMetadataLoaded();
            }
        };

        // Check immediately (next tick)
        setTimeout(immediateCheck, 50);

        // Fallback: if metadata doesn't load within 3 seconds, check again
        const timeoutId = setTimeout(() => {
            if (!hasLoadedMetadata) {
                console.log(`  ${selected.track.name} - metadata timeout, checking existing duration`);
                if (audioElement.duration && !isNaN(audioElement.duration)) {
                    console.log(`  ${selected.track.name} - has existing duration: ${audioElement.duration}`);
                    // Apply stored seek time if available
                    if (state.storedSeekTime !== null && state.storedSeekTime !== undefined) {
                        console.log(`  Applying stored seekTime (${state.storedSeekTime}s) to ${selected.track.name}`);
                        audioElement.currentTime = state.storedSeekTime;
                    }
                    onMetadataLoaded();
                }
            }
        }, 3000);
        timeoutIds.push(timeoutId);

        audioElements.push(audioElement);
    });

    console.log('Total audio elements to prepare:', audioElements.length);

    state.isPlaying = true;
    showToast(`🎵 正在播放 ${state.selectedTracks.length} 个音轨`, 'success');
    updatePlayState();
    startRealtimeVisualization();
}

/**
 * Play original (non-separated) file for quality check
 */
function playOriginalFile() {
    if (!state.selectedFile || !state.selectedFile.name) {
        showToast('未找到音频文件', 'error');
        return;
    }

    if (!state.apiConnected) {
        showToast('API 未连接', 'error');
        return;
    }

    const filename = state.selectedFile.name;
    const audioUrl = `${API_BASE_URL}/tracks/audio/original/${encodeURIComponent(filename)}`;

    // Bug Fix #3: Save current position before any changes
    // This preserves position when resuming from pause
    if (window.originalAudioPlayer && window.originalAudioPlayer.currentTime && !isNaN(window.originalAudioPlayer.currentTime)) {
        state.originalFilePosition = window.originalAudioPlayer.currentTime;
        console.log('Saved position from existing original audio player:', state.originalFilePosition);
    }

    // Use existing audio element or create new one
    if (!window.originalAudioPlayer) {
        window.originalAudioPlayer = new Audio();
        window.originalAudioPlayer.dataset.track = 'original';
    }

    // Stop any currently playing audio
    if (window.originalAudioPlayer) {
        window.originalAudioPlayer.pause();
    }

    // Stop any separated track playback
    const existingSeparatedAudio = document.querySelectorAll('audio[data-track]:not([data-track="original"])');
    existingSeparatedAudio.forEach(audio => audio.pause());

    window.originalAudioPlayer.src = audioUrl;

    // Connect to Web Audio API analyser for waveform visualization
    initAudioContext();
    connectAudioToAnalyser(window.originalAudioPlayer);

    // Set up event listeners for progress tracking and state updates
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
        const errorMsg = err.message || '未知错误';
        console.error('Error details:', {
            type: err.type,
            message: errorMsg,
            code: err.code,
            target: err.target?.src,
            readyState: err.target?.readyState,
            networkState: err.target?.networkState
        });
        showToast('播放失败: ' + errorMsg, 'error');
    };

    // Note: We intentionally do NOT update the now-playing-card UI
    // This allows users to click play and wait for separation without
    // the UI changing, so they can listen while processing happens in background

    window.originalAudioPlayer.play().then(() => {
        console.log('Playing original file:', filename);
        showToast('🎵 正在播放预览', 'info');
    }).catch(err => {
        console.error('Play error:', err);
        showToast('播放失败: ' + err.message, 'error');
    });
}

/**
 * Handle timeupdate for original file player
 */
function handleOriginalTimeUpdate() {
    if (!window.originalAudioPlayer) return;

    const audio = window.originalAudioPlayer;
    if (audio.duration && !isNaN(audio.duration)) {
        const progress = (audio.currentTime / audio.duration) * 100;
        if (elements.seekBar) elements.seekBar.value = progress;
        if (elements.currentTime) {
            elements.currentTime.textContent = formatTime(audio.currentTime);
        }
        if (elements.totalTime) {
            elements.totalTime.textContent = formatTime(audio.duration);
        }
        // Bug Fix #3: Persist position to state so it survives pause/play cycles
        state.originalFilePosition = audio.currentTime;
    }
}

/**
 * Handle loadedmetadata for original file player
 */
function handleOriginalMetadataLoaded() {
    if (!window.originalAudioPlayer || !window.originalAudioPlayer.duration) return;
    const duration = window.originalAudioPlayer.duration;
    if (elements.totalTime) {
        elements.totalTime.textContent = formatTime(duration);
    }
    console.log('Original file metadata loaded:', duration, 'seconds');

    // Bug Fix #3: Restore saved position from playOriginalFile
    // This takes precedence over pendingSeekPosition (which is for user-initiated seeks)
    if (state.originalFilePosition > 0) {
        const position = state.originalFilePosition;
        console.log('Restoring saved original file position:', position, 's');
        window.originalAudioPlayer.currentTime = position;
        state.originalFilePosition = 0;  // Clear after restoring
    }
    // Apply pending seek position if exists (only if no saved position was restored)
    else if (state.pendingSeekPosition !== null) {
        const seekTime = (state.pendingSeekPosition / 100) * duration;
        console.log('Applying pending seek to original file:', state.pendingSeekPosition, '% ->', seekTime, 's');
        window.originalAudioPlayer.currentTime = seekTime;
        state.pendingSeekPosition = null;
    }
}

/**
 * Handle play event for original file player
 */
function handleOriginalPlay() {
    state.isPlaying = true;
    updatePlayState();
    startRealtimeVisualization();
    // Note: We intentionally do NOT update now-playing-card
    // Users can keep listening while waiting for separation
}

/**
 * Handle pause event for original file player
 */
function handleOriginalPause() {
    // Check if all audio elements (including original) are paused
    const allAudio = document.querySelectorAll('audio[data-track]');
    let allPaused = true;
    for (const audio of allAudio) {
        if (!audio.paused) {
            allPaused = false;
            break;
        }
    }
    // Also check original audio player
    if (window.originalAudioPlayer && !window.originalAudioPlayer.paused) {
        allPaused = false;
    }

    // Bug Fix #5: Only update state if it's currently playing
    // This prevents race condition with pause() which already set isPlaying = false
    if (allPaused && state.isPlaying) {
        state.isPlaying = false;
        updatePlayState();
        stopRealtimeVisualization();
    }
}

/**
 * Handle ended event for original file player
 */
function handleOriginalEnded() {
    state.isPlaying = false;
    updatePlayState();
    stopRealtimeVisualization();
}

/**
 * Helper function to actually start playback
 */
function startPlayback(audioElements) {
    console.log('=== startPlayback() called ===');
    console.log('Starting playback on', audioElements.length, 'audio elements');

    audioElements.forEach(audio => {
        console.log('  Playing:', audio.dataset.track);
        audio.play().then(() => {
            console.log('  Successfully started playing:', audio.dataset.track);
            console.log('  currentTime after play:', audio.currentTime);
        }).catch(err => {
            console.error('Playback error for', audio.dataset.track, ':', err);
            showToast(`播放失败: ${audio.dataset.track}`, 'error');
        });
    });

    // Start periodic sync check for multi-track playback
    if (state.selectedTracks.length > 1) {
        startPeriodicSync();
    }
}

/**
 * Start periodic sync check during playback
 * Ensures tracks stay in sync during long playback
 */
let syncInterval = null;

function startPeriodicSync() {
    // Clear any existing interval first
    if (syncInterval) {
        clearInterval(syncInterval);
    }

    // Check every 1 second for drift
    syncInterval = setInterval(() => {
        if (state.isPlaying && state.selectedTracks.length > 1) {
            syncAllAudio();
        }
    }, 1000);

    console.log('Periodic sync check started (1 second interval)');
}

/**
 * Stop periodic sync check
 */
function stopPeriodicSync() {
    if (syncInterval) {
        clearInterval(syncInterval);
        syncInterval = null;
        console.log('Periodic sync check stopped');
    }
}

/**
 * Toggle Play/Pause - Unified play/pause toggle for the main button
 */
function togglePlayPause() {
    console.log('=== togglePlayPause() called ===');
    console.log('Current state - isPlaying:', state.isPlaying);

    if (state.isPlaying) {
        // Currently playing -> Pause
        console.log('Pausing playback');
        pause();
    } else {
        // Currently stopped/paused -> Play or Resume
        const existingAudio = document.querySelectorAll('audio[data-track]');
        if (existingAudio.length > 0) {
            console.log('Resuming playback');
            resume();
        } else {
            console.log('Starting playback');
            play();
        }
    }
}

/**
 * Pause - Pause all audio elements
 */
function pause() {
    console.log('=== pause() called ===');
    pauseAllAudio();

    // Also pause original audio player if exists
    if (window.originalAudioPlayer && !window.originalAudioPlayer.paused) {
        window.originalAudioPlayer.pause();
    }

    state.isPlaying = false;
    updatePlayState();
    stopRealtimeVisualization();
    stopPeriodicSync();
    showToast('已暂停', 'info');
}

/**
 * Resume - Resume all paused audio elements
 * This is called when clicking play while already having audio elements loaded
 */
function resume() {
    console.log('=== resume() called ===');

    // Check if there are any paused audio elements with tracks in selectedTracks
    const allAudio = document.querySelectorAll('audio[data-track]');
    if (allAudio.length === 0) {
        console.log('No audio elements found, falling back to full play()');
        play();
        return;
    }

    // Bug Fix #3: Verify that playing audio elements match current selected tracks
    const selectedTrackNames = new Set(state.selectedTracks.map(t => t.track.name));
    let hasMismatch = false;
    allAudio.forEach(audio => {
        if (!selectedTrackNames.has(audio.dataset.track)) {
            console.log(`Audio element ${audio.dataset.track} not in current selection`);
            hasMismatch = true;
        }
    });

    if (hasMismatch) {
        console.log('Audio elements don\'t match current selection, stopping and recreating');
        stopAllAudio();
        play();  // Recreate with current selection
        return;
    }

    // Check if all audio elements are actually paused (not stopped)
    // Bug Fix #1: Removed `|| audio.currentTime === 0` check
    // A paused audio at position 0 is still valid to resume
    let allPaused = true;
    allAudio.forEach(audio => {
        if (!audio.paused) {
            allPaused = false;
        }
    });

    if (!allPaused) {
        console.log('Audio elements are not all paused, using full play()');
        play();
        return;
    }

    // Collect all play promises
    const playPromises = [];
    allAudio.forEach(audio => {
        if (audio.duration && !isNaN(audio.duration)) {
            console.log(`Resuming: ${audio.dataset.track} at ${audio.currentTime}s`);
            playPromises.push(audio.play());
        } else {
            console.log(`Skipping resume for ${audio.dataset.track} - no valid duration`);
        }
    });

    if (playPromises.length === 0) {
        console.log('No audio elements could be resumed, using full play()');
        play();
        return;
    }

    // Wait for all play promises to complete, then update UI
    Promise.allSettled(playPromises).then(results => {
        const resumedCount = results.filter(r => r.status === 'fulfilled').length;

        console.log(`Resume promises completed: ${resumedCount}/${results.length} succeeded`);

        if (resumedCount > 0) {
            state.isPlaying = true;
            updatePlayState();
            startRealtimeVisualization();
            // Start periodic sync check for multi-track playback
            if (state.selectedTracks.length > 1) {
                startPeriodicSync();
            }
            showToast(`🎵 恢复播放 ${resumedCount} 个音轨`, 'success');
        } else {
            console.log('All resume promises rejected, using full play()');
            play();
        }
    }).catch(err => {
        console.error('Error during resume promise resolution:', err);
        play();
    });
}

/**
 * Stop - Stop all audio elements and reset
 */
function stop() {
    stopAllAudio();
    state.isPlaying = false;
    updatePlayState();
    stopRealtimeVisualization();
    stopPeriodicSync();

    // Reset seek bar and time display
    if (elements.seekBar) elements.seekBar.value = 0;
    if (elements.currentTime) elements.currentTime.textContent = '0:00';

    // Clear pending seek position and stored seek time
    state.pendingSeekPosition = null;
    state.storedSeekTime = null;
    state.originalFilePosition = 0;  // Bug Fix #3: Also clear original file position

    showToast('已停止', 'info');
}

/**
 * Seek - Seek all playing tracks
 */
function seek() {
    console.log('=== seek() called ===');
    console.log('Selected tracks:', state.selectedTracks.length);
    console.log('Is playing:', state.isPlaying);

    const seekPercent = elements.seekBar.value;
    console.log('Seek bar value:', seekPercent);

    // Determine which audio source is active
    // Check if we're playing separated tracks (has selected tracks AND separated track audio elements exist)
    const separatedAudio = document.querySelectorAll('audio[data-track]:not([data-track="original"])');
    const hasSeparatedTracksPlaying = state.selectedTracks.length > 0 && separatedAudio.length > 0;

    // Check if original audio is currently playing
    const isOriginalPlaying = window.originalAudioPlayer && !window.originalAudioPlayer.paused;

    if (hasSeparatedTracksPlaying) {
        // Seek separated tracks - fall through to the main seek logic below
        console.log('Seeking separated tracks');
    } else if (isOriginalPlaying) {
        // Original file is actively playing - seek it directly
        console.log('Original file is playing, seeking it');
        const seekTime = (seekPercent / 100) * window.originalAudioPlayer.duration;
        console.log(`Seeking original file to: ${seekTime}s (${seekPercent}%)`);
        window.originalAudioPlayer.currentTime = seekTime;
        return;
    } else if (state.selectedTracks.length > 0) {
        // Tracks are selected but no separated audio elements exist yet
        // Store the seek position for when audio elements are created
        console.log('Tracks selected but no audio elements yet - storing pending seek position:', seekPercent);
        state.pendingSeekPosition = seekPercent;
        return;
    } else if (state.selectedTracks.length === 0) {
        // No tracks selected yet - store the seek position for later
        console.log('No tracks selected - storing pending seek position:', seekPercent);
        state.pendingSeekPosition = seekPercent;
        return;
    }

    // Find audio element with valid duration as reference
    const allAudio = document.querySelectorAll('audio[data-track]');
    console.log('Found audio elements:', allAudio.length);

    // Display all audio element info for debugging
    for (const audio of allAudio) {
        console.log(`  Audio ${audio.dataset.track}: duration=${audio.duration}, currentTime=${audio.currentTime}`);
    }

    // Find first audio element with a valid duration
    let mainAudio = null;
    for (const audio of allAudio) {
        if (audio.duration && !isNaN(audio.duration) && audio.duration > 0) {
            mainAudio = audio;
            console.log(`Selected ${audio.dataset.track} as reference (has duration: ${audio.duration})`);
            break;
        }
    }

    if (!mainAudio) {
        console.log('No audio element has valid duration yet - storing pending seek position for when audio loads');
        state.pendingSeekPosition = seekPercent;
        return;
    }

    // Bug Fix #5: Validate seek time calculation before applying
    const seekTime = (seekPercent / 100) * mainAudio.duration;

    console.log('Seek info:', {
        percent: seekPercent,
        targetTime: seekTime,
        currentDuration: mainAudio.duration
    });

    // Bug Fix #5: Check if seek time is valid
    if (isNaN(seekTime) || seekTime < 0 || seekTime > mainAudio.duration) {
        console.log('Invalid seek time calculated:', seekTime, '- skipping seek');
        return;
    }

    // Seek all audio elements to the same time with high precision
    allAudio.forEach(audio => {
        if (audio.duration && !isNaN(audio.duration) && audio.duration > 0) {
            // Bug Fix #5: Validate target time for each audio element
            const targetSeekTime = (seekPercent / 100) * audio.duration;
            if (isNaN(targetSeekTime) || targetSeekTime < 0 || targetSeekTime > audio.duration) {
                console.log(`Skipping ${audio.dataset.track} - invalid seek time: ${targetSeekTime}`);
                return;
            }

            console.log(`Seeking ${audio.dataset.track} to ${targetSeekTime}`);
            audio.currentTime = targetSeekTime;
        } else {
            console.log(`Skipping ${audio.dataset.track} - no valid duration`);
        }
    });

    // Clear pending seek position since we've successfully seeked
    state.pendingSeekPosition = null;

    // Also update the seek bar position to match the actual position
    updateProgress();
}

/**
 * Sync all playing audio elements to the same position
 * Called periodically or when tracks are added/removed
 */
function syncAllAudio() {
    const allAudio = document.querySelectorAll('audio[data-track]');

    // Find reference audio (playing with valid duration)
    let refAudio = null;
    for (const audio of allAudio) {
        if (!audio.paused && audio.duration && !isNaN(audio.duration)) {
            refAudio = audio;
            break;
        }
    }

    if (!refAudio) return; // Nothing to sync

    const refTime = refAudio.currentTime;

    // Sync all other audio elements to reference
    allAudio.forEach(audio => {
        if (audio !== refAudio && !audio.paused && audio.duration && !isNaN(audio.duration)) {
            // Only sync if drift is significant (> 0.05 seconds - tightened for better precision)
            const drift = Math.abs(audio.currentTime - refTime);
            if (drift > 0.05) {
                audio.currentTime = refTime;
                console.log(`Synced ${audio.dataset.track} (drift: ${drift.toFixed(3)}s)`);
            }
        }
    });
}

/**
 * Update Progress - Use first audio element as reference
 */
function updateProgress() {
    // Find the audio element that's currently playing and has valid duration
    const allAudio = document.querySelectorAll('audio[data-track]');

    let mainAudio = null;

    // First, check if original audio player is playing (only when no separated tracks selected)
    if (state.selectedTracks.length === 0 && window.originalAudioPlayer &&
        !window.originalAudioPlayer.paused &&
        window.originalAudioPlayer.duration && !isNaN(window.originalAudioPlayer.duration)) {
        mainAudio = window.originalAudioPlayer;
    }

    // Then prefer a playing separated track audio element with duration
    if (!mainAudio && allAudio.length > 0) {
        for (const audio of allAudio) {
            if (!audio.paused && audio.duration && !isNaN(audio.duration)) {
                mainAudio = audio;
                break;
            }
        }
    }

    // Fallback: any separated track audio element with duration (even if paused)
    if (!mainAudio && allAudio.length > 0) {
        for (const audio of allAudio) {
            if (audio.duration && !isNaN(audio.duration)) {
                mainAudio = audio;
                break;
            }
        }
    }

    // For original file playback (no separated tracks selected)
    if (!mainAudio && state.selectedTracks.length === 0 && window.originalAudioPlayer &&
        window.originalAudioPlayer.duration && !isNaN(window.originalAudioPlayer.duration)) {
        mainAudio = window.originalAudioPlayer;
    }

    if (mainAudio && mainAudio.duration && !isNaN(mainAudio.duration)) {
        const progress = (mainAudio.currentTime / mainAudio.duration) * 100;
        if (elements.seekBar) elements.seekBar.value = progress;
        if (elements.currentTime) {
            elements.currentTime.textContent = formatTime(mainAudio.currentTime);
        }
    }

    // Periodically sync all audio elements for precision (every ~500ms based on timeupdate rate)
    if (state.isPlaying && allAudio.length > 1) {
        syncAllAudio();
    }
}

/**
 * Update Duration
 */
function updateDuration() {
    console.log('=== updateDuration() called ===');

    // Use first available audio element with duration
    const allAudio = document.querySelectorAll('audio[data-track]');
    console.log('Found audio elements:', allAudio.length);

    let mainAudio = null;

    // First check original audio player (only when no separated tracks selected)
    if (state.selectedTracks.length === 0 && window.originalAudioPlayer &&
        window.originalAudioPlayer.duration && !isNaN(window.originalAudioPlayer.duration)) {
        mainAudio = window.originalAudioPlayer;
    }

    // Then find a separated track audio element with valid duration
    if (!mainAudio && allAudio.length > 0) {
        for (const audio of allAudio) {
            console.log(`  Checking ${audio.dataset.track}: duration=${audio.duration}, isNaN=${isNaN(audio.duration)}`);
            if (audio.duration && !isNaN(audio.duration)) {
                mainAudio = audio;
                console.log(`  Found valid duration on ${audio.dataset.track}: ${audio.duration}`);
                break;
            }
        }
    }

    // For original file playback (no separated tracks selected)
    if (!mainAudio && state.selectedTracks.length === 0 && window.originalAudioPlayer &&
        window.originalAudioPlayer.duration && !isNaN(window.originalAudioPlayer.duration)) {
        mainAudio = window.originalAudioPlayer;
    }

    if (mainAudio && mainAudio.duration && !isNaN(mainAudio.duration)) {
        console.log('Setting total time to:', formatTime(mainAudio.duration));
        if (elements.totalTime) {
            elements.totalTime.textContent = formatTime(mainAudio.duration);
        }
        drawStaticWaveform();
    } else {
        console.log('No valid audio with duration found');
    }
}

/**
 * Update total time display when tracks are selected (before playing)
 */
function updateTotalTimeForSelectedTracks() {
    if (!elements.totalTime || state.selectedTracks.length === 0) {
        return;
    }

    // Get the first selected track's duration from the track data
    const firstSelected = state.selectedTracks[0];
    if (firstSelected && firstSelected.track && firstSelected.track.duration) {
        elements.totalTime.textContent = formatTime(firstSelected.track.duration);
    }
}

/**
 * Update the now-playing display to show all selected tracks with icons (minimal design)
 * Also shows the song info bar to remind user which song they're working with
 */
function updateNowPlayingDisplay() {
    if (!elements.nowPlayingContent) return;

    // Generate song info bar if we have an uploaded file
    let songInfoHTML = '';
    if (state.uploadedFile && state.uploadedFile.name) {
        songInfoHTML = generateSongInfoBar(state.uploadedFile);
    }

    // If no tracks are selected, show the song info bar + play original button
    if (state.selectedTracks.length === 0) {
        // Show play original button if we have an uploaded file (original song available)
        let playOriginalHTML = '';
        if (state.uploadedFile && state.uploadedFile.name) {
            playOriginalHTML = `
                <button id="playOriginalBtn" class="btn-primary" style="flex: 1; min-width: 140px;">
                    <span class="icon">▶</span> 播放完整歌曲
                </button>
            `;
            // Also update total time display with the original file's duration
            if (elements.totalTime && state.uploadedFile.duration) {
                elements.totalTime.textContent = formatTime(state.uploadedFile.duration);
            }
        } else {
            playOriginalHTML = `
                <span class="placeholder-text">
                    <span class="icon">🎵</span>
                    选择音轨开始播放
                </span>
            `;
        }

        elements.nowPlayingContent.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
                ${songInfoHTML}
                <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: center; min-height: 32px;">
                    ${playOriginalHTML}
                </div>
            </div>
        `;

        // Add click handler for play original button
        if (state.uploadedFile && state.uploadedFile.name) {
            const playOriginalBtn = document.getElementById('playOriginalBtn');
            if (playOriginalBtn) {
                playOriginalBtn.addEventListener('click', () => {
                    console.log('Play original button clicked');
                    play();
                });
            }
        }
        return;
    }

    // Group tracks by type for cleaner display
    const groupedTracks = state.selectedTracks.reduce((acc, t) => {
        const info = getTrackIconInfo(t.track.name);
        if (!acc[info.class]) {
            acc[info.class] = { icon: info.icon, class: info.class, displayName: info.displayName, count: 0 };
        }
        acc[info.class].count++;
        return acc;
    }, {});

    // Create minimal track type badges
    const badges = Object.values(groupedTracks)
        .map(g => `<span class="track-icon-badge ${g.class}"><span class="icon">${g.icon}</span> ${g.displayName}${g.count > 1 ? `×${g.count}` : ''}</span>`)
        .join(' ');

    elements.nowPlayingContent.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
            ${songInfoHTML}
            <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: center; min-height: 32px;">
                ${badges}
            </div>
        </div>
    `;
}

/**
 * Handle Track End
 */
function handleTrackEnd() {
    if (!state.isLooping) {
        stopRealtimeVisualization();
        state.isPlaying = false;
        updatePlayState();

        // Clear seek-related state when track ends
        state.pendingSeekPosition = null;
        state.storedSeekTime = null;
    }
}

/**
 * Update Play State
 * Updates the unified play/pause toggle button and stop button based on current state
 */
function updatePlayState() {
    if (!elements.playPauseBtn) return;

    // Check if audio is available (either selected tracks or original file)
    const hasAudio = state.selectedTracks.length > 0 ||
                     state.selectedFile !== null ||
                     (window.originalAudioPlayer && window.originalAudioPlayer.src);

    // Play/Pause Toggle: Always enabled when audio is available
    if (hasAudio) {
        elements.playPauseBtn.disabled = false;
        elements.playPauseBtn.style.opacity = '1';

        // Update icon and visual state
        if (state.isPlaying) {
            // Playing state - show pause icon, amber glow
            if (elements.playPauseIcon) {
                elements.playPauseIcon.textContent = '⏸';
            }
            elements.playPauseBtn.style.background = 'rgba(251, 191, 36, 0.25)';
            elements.playPauseBtn.style.borderColor = 'rgba(251, 191, 36, 0.6)';
            elements.playPauseBtn.style.boxShadow = '0 0 15px rgba(251, 191, 36, 0.3)';
        } else {
            // Paused/Stopped state - show play icon, no glow
            if (elements.playPauseIcon) {
                elements.playPauseIcon.textContent = '▶';
            }
            elements.playPauseBtn.style.background = '';
            elements.playPauseBtn.style.borderColor = '';
            elements.playPauseBtn.style.boxShadow = '';
        }
    } else {
        // No audio available - disable toggle
        elements.playPauseBtn.disabled = true;
        elements.playPauseBtn.style.opacity = '0.5';
        elements.playPauseBtn.style.background = '';
        elements.playPauseBtn.style.borderColor = '';
        elements.playPauseBtn.style.boxShadow = '';
        if (elements.playPauseIcon) {
            elements.playPauseIcon.textContent = '▶';
        }
    }

    // Stop button: enabled when audio is available (playing or paused)
    // This allows users to stop/reset even when paused
    if (elements.stopBtn) {
        if (hasAudio) {
            elements.stopBtn.disabled = false;
            elements.stopBtn.style.opacity = '1';
            elements.stopBtn.style.background = 'rgba(239, 68, 68, 0.2)';
            elements.stopBtn.style.borderColor = 'rgba(239, 68, 68, 0.5)';
            elements.stopBtn.style.boxShadow = '0 0 15px rgba(239, 68, 68, 0.3)';
        } else {
            elements.stopBtn.disabled = true;
            elements.stopBtn.style.opacity = '0.6';
            elements.stopBtn.style.background = '';
            elements.stopBtn.style.borderColor = '';
            elements.stopBtn.style.boxShadow = '';
        }
    }
}

/**
 * Start Real-time Visualization
 */
function startRealtimeVisualization() {
    if (!elements.waveform || !waveformCtx) {
        console.warn('Waveform canvas not available');
        return;
    }

    try {
        initAudioContext();

        if (state.audioContext.state === 'suspended') {
            state.audioContext.resume();
        }

        elements.vizMode.textContent = '实时频谱';
        visualizeRealtime();
    } catch (error) {
        console.log('Falling back to simulated visualization:', error);
        elements.vizMode.textContent = '模拟波形';
        startWaveformAnimation();
    }
}

/**
 * Stop Real-time Visualization
 */
function stopRealtimeVisualization() {
    if (animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
    }
}

/**
 * Initialize Web Audio API
 * Note: Individual audio elements will connect to the analyser when played
 */
function initAudioContext() {
    if (state.audioContext) return;

    const AudioContext = window.AudioContext || window.webkitAudioContext;
    state.audioContext = new AudioContext();
    state.analyser = state.audioContext.createAnalyser();
    state.analyser.fftSize = 256;

    // Connect analyser to destination for audio output
    // When we connect a MediaElementSourceNode to the analyser, the audio element
    // stops outputting to speakers directly, so we need to route through Web Audio API
    state.analyser.connect(state.audioContext.destination);
}

/**
 * Connect an audio element to the Web Audio API analyser for visualization
 * @param {HTMLAudioElement} audioElement - The audio element to connect
 */
function connectAudioToAnalyser(audioElement) {
    if (!state.audioContext || !state.analyser || !audioElement) return;

    try {
        // Check if already connected to avoid duplicate connections
        if (audioElement._analyserConnected) {
            return;
        }

        // Create media element source and connect to analyser
        const source = state.audioContext.createMediaElementSource(audioElement);
        source.connect(state.analyser);

        // The analyser is already connected to destination in initAudioContext()
        // so the audio will flow: audioElement -> MediaElementSource -> analyser -> destination (speakers)

        audioElement._analyserConnected = true;
        audioElement._audioSource = source; // Store reference to prevent garbage collection
    } catch (error) {
        // This may fail if the audio element was already connected or if the context is closed
        console.warn('Could not connect audio to analyser:', error);
    }
}

/**
 * Real-time Frequency Visualization
 */
function visualizeRealtime() {
    if (!state.analyser || !state.isPlaying || !waveformCtx || !elements.waveform) {
        return;
    }

    const bufferLength = state.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const width = elements.waveform.width;
    const height = elements.waveform.height;

    const draw = () => {
        if (!state.isPlaying) return;

        animationId = requestAnimationFrame(draw);

        state.analyser.getByteFrequencyData(dataArray);

        // Clear canvas
        waveformCtx.fillStyle = '#1a1a24';
        waveformCtx.fillRect(0, 0, width, height);

        // Draw frequency bars
        const barCount = Math.min(bufferLength, 64); // Limit bars for cleaner look
        const barWidth = width / barCount;

        for (let i = 0; i < barCount; i++) {
            const dataIndex = Math.floor((i / barCount) * bufferLength);
            const barHeight = (dataArray[dataIndex] / 255) * height * 0.9;

            // Gradient color
            const hue = (i / barCount) * 60 + 240; // Blue to purple
            const alpha = 0.6 + (dataArray[dataIndex] / 255) * 0.4;
            waveformCtx.fillStyle = `hsla(${hue}, 80%, 60%, ${alpha})`;

            const x = i * barWidth;
            const y = height - barHeight;

            // Rounded bar
            const radius = 2;
            waveformCtx.beginPath();
            waveformCtx.moveTo(x + radius, height);
            waveformCtx.lineTo(x + radius, y);
            waveformCtx.lineTo(x + barWidth - radius, y);
            waveformCtx.lineTo(x + barWidth - radius, height);
            waveformCtx.closePath();
            waveformCtx.fill();

            // Add glow for high values
            if (dataArray[dataIndex] > 200) {
                waveformCtx.shadowBlur = 10;
                waveformCtx.shadowColor = `hsla(${hue}, 80%, 60%, 0.5)`;
                waveformCtx.fill();
                waveformCtx.shadowBlur = 0;
            }
        }

        // Add indicator for multi-track mode
        const selectedCount = state.selectedTracks.length;
        if (selectedCount > 1) {
            // Draw semi-transparent background for the indicator
            waveformCtx.fillStyle = 'rgba(139, 92, 246, 0.3)';
            waveformCtx.fillRect(10, height - 30, 90, 20);

            // Draw text
            waveformCtx.fillStyle = '#fff';
            waveformCtx.font = '12px sans-serif';
            waveformCtx.fillText(`${selectedCount} tracks`, 20, height - 15);
        }
    };

    draw();
}

/**
 * Simulated Waveform Animation
 */
function startWaveformAnimation() {
    if (animationId || !waveformCtx || !elements.waveform) return;
    animateWaveform();
}

function animateWaveform() {
    if (!elements.audioPlayer.duration) {
        animationId = requestAnimationFrame(animateWaveform);
        return;
    }

    const width = elements.waveform.width;
    const height = elements.waveform.height;
    const currentTime = elements.audioPlayer.currentTime;
    const duration = elements.audioPlayer.duration;

    // Clear
    waveformCtx.fillStyle = '#1a1a24';
    waveformCtx.fillRect(0, 0, width, height);

    // Progress background
    const progressX = (currentTime / duration) * width;
    waveformCtx.fillStyle = 'rgba(139, 92, 246, 0.2)';
    waveformCtx.fillRect(0, 0, progressX, height);

    // Waveform
    waveformCtx.strokeStyle = '#a78bfa';
    waveformCtx.lineWidth = 2;
    waveformCtx.beginPath();

    const centerY = height / 2;
    const amplitude = height / 3;
    const timeScale = width / duration;

    for (let x = 0; x < width; x++) {
        const time = (x / timeScale);
        const y = centerY + Math.sin(time * 10) * amplitude * 0.5 + Math.sin(time * 27) * amplitude * 0.3;
        if (x === 0) {
            waveformCtx.moveTo(x, y);
        } else {
            waveformCtx.lineTo(x, y);
        }
    }

    waveformCtx.stroke();

    // Playhead
    waveformCtx.fillStyle = '#fbbf24';
    waveformCtx.fillRect(progressX - 2, 0, 4, height);

    animationId = requestAnimationFrame(animateWaveform);
}

/**
 * Draw Static Waveform (when audio is loaded)
 */
function drawStaticWaveform() {
    if (!waveformCtx || !elements.waveform) return;

    const width = elements.waveform.width;
    const height = elements.waveform.height;

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
        if (x === 0) {
            waveformCtx.moveTo(x, y);
        } else {
            waveformCtx.lineTo(x, y);
        }
    }

    waveformCtx.stroke();
}

/**
 * Draw Empty Waveform
 */
function drawEmptyWaveform() {
    if (!waveformCtx || !elements.waveform) return;

    const width = elements.waveform.width;
    const height = elements.waveform.height;

    waveformCtx.fillStyle = '#1a1a24';
    waveformCtx.fillRect(0, 0, width, height);

    waveformCtx.fillStyle = '#64748b';
    waveformCtx.font = '14px var(--font-sans)';
    waveformCtx.textAlign = 'center';
    waveformCtx.textBaseline = 'middle';
    waveformCtx.fillText('等待播放...', width / 2, height / 2);
}

/**
 * Toggle Upload Panel
 */
function toggleUploadPanel() {
    // Prevent closing upload panel during active upload
    if (state.isUploading) {
        showToast('上传中，请等待完成', 'warning');
        return;
    }

    // Prevent opening if upload is locked (tracks exist)
    if (state.uploadLocked && !state.uploadVisible) {
        showToast('已上传文件，请先清除再上传新文件', 'warning');
        return;
    }

    state.uploadVisible = !state.uploadVisible;

    if (state.uploadVisible) {
        elements.uploadPanel.classList.remove('hidden');
        if (elements.uploadBtn) {
            elements.uploadBtn.textContent = '✕ 关闭';
        }
    } else {
        elements.uploadPanel.classList.add('hidden');
        if (elements.uploadBtn) {
            elements.uploadBtn.textContent = '+ 上传';
        }
    }
}

/**
 * Handle File Select
 * Upload file to server immediately, then show preview
 */
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file size (100MB max)
    if (file.size > 100 * 1024 * 1024) {
        showToast('文件太大，最大支持 100MB', 'error');
        return;
    }

    // Validate file type
    if (!file.type.startsWith('audio/')) {
        showToast('请上传音频文件', 'error');
        return;
    }

    // Upload file to server immediately and show preview after
    uploadFileForPreview(file);
}

/**
 * Upload file to server and show preview
 * Clears existing files first if an uploadedFile already exists
 */
async function uploadFileForPreview(file) {
    if (!state.apiConnected) {
        showToast('API 未连接', 'error');
        return;
    }

    // NEW: Clear existing files before uploading a new one (one file at a time)
    if (state.uploadedFile && state.uploadedFile.name) {
        console.log('Clearing existing uploaded file before new upload:', state.uploadedFile.name);
        try {
            await fetch(`${API_BASE_URL}/separation/clear`, { method: 'POST' });
            // Clear state
            state.uploadedFile = { name: null, path: null, size: null, duration: null, source: null, timestamp: null, isSeparated: false };
            state.selectedFile = null;  // Keep deprecated field in sync
        } catch (clearError) {
            console.warn('Failed to clear existing files:', clearError);
        }
    }

    // Set processing state
    state.processing = true;
    state.processingType = 'upload';
    state.isUploading = true;

    if (elements.uploadBtn) {
        elements.uploadBtn.disabled = true;
        elements.uploadBtn.textContent = '⏳ 上传中';
    }

    // Create FormData to upload file
    const formData = new FormData();
    formData.append('file', file);

    // Show uploading state in UI
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) uploadDropzone.classList.add('hidden');
    elements.uploadProgress.classList.remove('hidden');
    updateProgressUI('正在上传...', 20);

    try {
        // Upload to server (save in storage/uploaded/)
        const response = await fetch(`${API_BASE_URL}/upload/preview`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            updateProgressUI('上传完成', 50);

            // Show file preview from server
            showFilePreviewFromServer(result.file_info);

            // NEW: Store in unified uploadedFile state
            state.uploadedFile = {
                name: result.file_info.name,
                path: `storage/uploaded/${result.file_info.name}`,  // Construct path
                size: result.file_info.size,
                duration: result.file_info.duration,
                source: 'upload',
                timestamp: Date.now(),
                isSeparated: false,
            };

            // NEW: Keep deprecated selectedFile in sync for backward compatibility
            state.selectedFile = {
                name: result.file_info.name,
                size: result.file_info.size,
                duration: result.file_info.duration,
                source: 'upload',
                isSeparated: false,
            };

            showToast('文件已上传，点击确认处理', 'success');
        }

    } catch (error) {
        console.error('Upload error:', error);
        showToast(`上传失败: ${error.message}`, 'error');
        updateProgressUI('上传失败', 0);

        // Reset UI after delay
        setTimeout(() => {
            cancelFilePreview();
        }, 2000);
    } finally {
        // Reset processing state
        state.isUploading = false;
        state.processing = false;
        state.processingType = null;
        if (elements.uploadBtn) {
            elements.uploadBtn.disabled = false;
            elements.uploadBtn.textContent = '+ 上传';
        }
    }
}

/**
 * Display file preview information from server response
 * Shows preview ONLY in now-playing-card, NOT in uploadPanel
 */
function showFilePreviewFromServer(fileInfo) {
    // Hide progress bar
    if (elements.uploadProgress) {
        elements.uploadProgress.classList.add('hidden');
    }

    // Hide process card (we're using now-playing card exclusively)
    if (elements.processCard) {
        elements.processCard.classList.add('hidden');
    }

    // Fold upload panel (hide it)
    if (elements.uploadPanel) {
        elements.uploadPanel.classList.add('hidden');
    }
    state.uploadVisible = false;

    // Show preview in now-playing-card with Process button
    showPreviewInNowPlayingCard(fileInfo, true);
}

/**
 * Generate compact song info bar HTML
 * Shows song info in a compact, persistent bar at the top of the now-playing card
 * Uses uploadedFile if fileInfo is not provided
 */
function generateSongInfoBar(fileInfo = null, source = null, status = 'ready') {
    // Use uploadedFile if no fileInfo provided (for backward compatibility)
    const info = fileInfo || state.uploadedFile;
    if (!info) {
        return '';
    }

    const sizeMB = (info.size / (1024 * 1024)).toFixed(1);
    const extension = info.name.split('.').pop() || '未知格式';
    const truncatedName = info.name.length > 30 ? info.name.substring(0, 30) + '...' : info.name;
    const src = source || info.source || 'upload';

    // Source badge
    const sourceBadge = src === 'youtube'
        ? '<span class="song-info-source">YouTube</span>'
        : '<span class="song-info-source">本地</span>';

    return `
        <div class="song-info-bar">
            <div class="song-info-icon">🎵</div>
            <div class="song-info-details">
                <div class="song-info-item">
                    <span class="song-info-label">文件名</span>
                    <span class="song-info-value truncated" title="${info.name}">${truncatedName}</span>
                </div>
                <div class="song-info-item">
                    <span class="song-info-label">时长</span>
                    <span class="song-info-value">${formatTime(info.duration)}</span>
                </div>
                <div class="song-info-item">
                    <span class="song-info-label">格式</span>
                    <span class="file-badge">${extension.toUpperCase()}</span>
                </div>
                ${sourceBadge}
            </div>
        </div>
    `;
}

/**
 * Show preview information in the now-playing-card div
 * This is displayed when uploadPanel is folded
 */
function showPreviewInNowPlayingCard(fileInfo, showProcessButton = true) {
    if (!elements.nowPlayingContent) return;

    const source = fileInfo.source || 'upload';

    // Determine button text and type based on source
    const buttonText = '开始分离';
    const buttonClass = 'btn-primary';

    const processButtonHTML = showProcessButton ? `
        <div style="display: flex; gap: 8px; margin-top: var(--space-md);">
            <button id="processNowBtn" class="${buttonClass}" style="flex: 1;">${buttonText}</button>
        </div>
    ` : '';

    elements.nowPlayingContent.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
            ${generateSongInfoBar(fileInfo, source, 'ready')}
            <div style="text-align: center; color: var(--text-muted); font-size: 0.95rem; margin-top: 4px;">
                🎧 点击下方按钮开始分离处理
            </div>
            ${processButtonHTML}
        </div>
    `;

    // Update now-playing header
    if (elements.nowPlayingHeader) {
        elements.nowPlayingHeader.textContent = '🎵 文件预览';
    }

    // Update dropzone visual state to show file was uploaded
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) {
        uploadDropzone.classList.remove('uploaded', 'disabled');
        uploadDropzone.classList.add('uploaded');
    }

    // Add click handler for the process button if it exists
    if (showProcessButton) {
        const processNowBtn = document.getElementById('processNowBtn');
        if (processNowBtn) {
            // NEW: Use unified processUploadedFile function for both upload and YouTube sources
            processNowBtn.addEventListener('click', processUploadedFile);
        }
    }
}

/**
 * Clear preview information from now-playing-card
 * Called when CLEAR button is clicked
 */
function clearPreviewFromNowPlayingCard() {
    if (!elements.nowPlayingContent) return;
    elements.nowPlayingContent.innerHTML = '<div class="placeholder-text">选择音轨开始播放</div>';

    // Reset dropzone visual state
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) {
        uploadDropzone.classList.remove('uploaded', 'disabled');
    }
}

/**
 * Change Process button to Clear button after separation completes
 * (This function is deprecated - now separation shows track list directly)
 */
function changeToClearButton() {
    // No longer needed - separation now shows track list directly in updateAfterSeparation()
}

/**
 * Reset Process button (when going back to initial state)
 * (This function is deprecated - now Process button is in now-playing card)
 */
function resetProcessButton() {
    // No longer needed - Process button is now in now-playing card
}

/**
 * Cancel file preview and reset upload UI
 */
function cancelFilePreview() {
    // Reset state
    state.selectedFile = null;

    // Reset file input
    if (elements.fileInput) {
        elements.fileInput.value = '';
    }

    // Show the upload dropzone again
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) uploadDropzone.classList.remove('hidden');

    // Hide process card
    if (elements.processCard) {
        elements.processCard.classList.add('hidden');
    }

    // Hide progress
    if (elements.uploadProgress) {
        elements.uploadProgress.classList.add('hidden');
    }

    // Remove processing state from upload panel
    if (elements.uploadPanel) {
        elements.uploadPanel.classList.remove('processing');
    }

    // Clear preview from now-playing card
    clearPreviewFromNowPlayingCard();

    // Reset the Process button state
    resetProcessButton();

    showToast('已取消选择', 'info');
}

/**
 * DEPRECATED: Use processUploadedFile() instead
 * Process the selected file (start separation)
 * File is already uploaded to storage/uploaded/, now process it
 * Uses Server-Sent Events (SSE) for real-time progress updates
 */
async function processSelectedFile() {
    // DEPRECATED: Use processUploadedFile() instead
    console.warn('processSelectedFile() is deprecated, use processUploadedFile() instead');
    if (!state.selectedFile) {
        showToast('请先选择文件', 'warning');
        return;
    }

    if (!state.apiConnected) {
        showToast('API 未连接', 'error');
        return;
    }

    // Hide progress section in uploadPanel (we show progress in now-playing card instead)
    elements.uploadProgress.classList.add('hidden');  // Hide the old progress bar in uploadPanel

    // File is already uploaded to storage/uploaded/
    // Now call separation to move and process it with streaming progress
    const formData = new FormData();
    formData.append('filename', state.selectedFile.name);

    // IMMEDIATE BUTTON DISABLE AND VISUAL FEEDBACK
    // Disable the Process button immediately
    if (elements.confirmUploadBtn) {
        elements.confirmUploadBtn.disabled = true;
        elements.confirmUploadBtn.textContent = '处理中...';
        elements.confirmUploadBtn.style.opacity = '0.6';
        elements.confirmUploadBtn.style.cursor = 'not-allowed';
    }

    // Disable other interactive elements in uploadPanel
    if (elements.cancelUploadBtn) {
        elements.cancelUploadBtn.disabled = true;
    }

    // Add processing state to upload panel (dims it, shows overlay "⏳ 处理中...")
    if (elements.uploadPanel) {
        elements.uploadPanel.classList.add('processing');
    }

    // Add disabled state to upload dropzone
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) {
        uploadDropzone.classList.remove('uploaded');
        uploadDropzone.classList.add('disabled');
    }

    // Show initial processing progress in now-playing card (not in uploadPanel)
    showProcessingInNowPlayingCard('准备分离...', 0, 0, 0);

    try {
        // Use SSE endpoint for real-time progress
        const response = await fetch(`${API_BASE_URL}/separation/separate_by_name_stream`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // Create EventSource for streaming progress
        // For streaming response, we need to use fetch with a ReadableStream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // Function to handle streaming data
        const processStream = async () => {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process complete SSE events (separated by double newlines)
                const events = buffer.split('\n\n');
                buffer = events.pop(); // Keep incomplete data in buffer

                for (const event of events) {
                    if (event.startsWith('data: ')) {
                        const dataStr = event.slice(6); // Remove 'data: ' prefix
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
        showToast(`分离失败: ${error.message}`, 'error');

        // Hide processing progress in now-playing card
        hideProcessingInNowPlayingCard();

        // Remove processing state from upload panel
        if (elements.uploadPanel) {
            elements.uploadPanel.classList.remove('processing');
        }

        // Restore dropzone to uploaded state (so user can retry)
        const uploadDropzone = document.querySelector('.upload-dropzone');
        if (uploadDropzone) {
            uploadDropzone.classList.remove('disabled');
            uploadDropzone.classList.add('uploaded');
        }

        // Re-enable the Process button on error
        if (elements.confirmUploadBtn) {
            elements.confirmUploadBtn.disabled = false;
            elements.confirmUploadBtn.textContent = '处理';
            elements.confirmUploadBtn.style.opacity = '1';
            elements.confirmUploadBtn.style.cursor = 'pointer';
        }
        if (elements.cancelUploadBtn) {
            elements.cancelUploadBtn.disabled = false;
        }
    }
}

/**
 * Unified file processing function - handles both direct upload and YouTube download
 * This replaces processSelectedFile() and separateYouTubeFile() with a single function
 * The file must already exist in storage/uploaded/ (either uploaded or downloaded)
 */
async function processUploadedFile() {
    // NEW: Use uploadedFile as source of truth
    if (!state.uploadedFile || !state.uploadedFile.name) {
        showToast('请先上传或下载音频文件', 'warning');
        return;
    }

    if (!state.apiConnected) {
        showToast('API 未连接', 'error');
        return;
    }

    // NEW: Validate file still exists on server
    try {
        const checkResponse = await fetch(`${API_BASE_URL}/tracks/info/${encodeURIComponent(state.uploadedFile.name)}`);
        if (!checkResponse.ok) {
            showToast('文件已过期，请重新上传', 'error');
            // Clear the expired file state
            state.uploadedFile = { name: null, path: null, size: null, duration: null, source: null, timestamp: null, isSeparated: false };
            state.selectedFile = null;
            clearPreviewFromNowPlayingCard();
            return;
        }
    } catch (error) {
        console.warn('File existence check failed:', error);
    }

    // Set processing state
    state.processing = true;
    state.processingType = 'separation';

    // Hide progress section in uploadPanel (we show progress in now-playing card instead)
    if (elements.uploadProgress) {
        elements.uploadProgress.classList.add('hidden');
    }

    // File is already uploaded to storage/uploaded/
    // Now call separation to process it with streaming progress
    const formData = new FormData();
    formData.append('filename', state.uploadedFile.name);

    // IMMEDIATE BUTTON DISABLE AND VISUAL FEEDBACK
    // Disable the Process button immediately
    if (elements.confirmUploadBtn) {
        elements.confirmUploadBtn.disabled = true;
        elements.confirmUploadBtn.textContent = '处理中...';
        elements.confirmUploadBtn.style.opacity = '0.6';
        elements.confirmUploadBtn.style.cursor = 'not-allowed';
    }

    // Disable other interactive elements in uploadPanel
    if (elements.cancelUploadBtn) {
        elements.cancelUploadBtn.disabled = true;
    }

    // Add processing state to upload panel (dims it, shows overlay "⏳ 处理中...")
    if (elements.uploadPanel) {
        elements.uploadPanel.classList.add('processing');
    }

    // Add disabled state to upload dropzone
    const uploadDropzone = document.querySelector('.upload-dropzone');
    if (uploadDropzone) {
        uploadDropzone.classList.remove('uploaded');
        uploadDropzone.classList.add('disabled');
    }

    // Stop any currently playing audio
    if (window.originalAudioPlayer && !window.originalAudioPlayer.paused) {
        window.originalAudioPlayer.pause();
    }
    state.isPlaying = false;
    updatePlayState();

    // Show initial processing progress in now-playing card
    showProcessingInNowPlayingCard('准备分离...', 0, 0, 0);

    try {
        // Use SSE endpoint for real-time progress
        const response = await fetch(`${API_BASE_URL}/separation/separate_by_name_stream`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // Create EventSource for streaming progress
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // Function to handle streaming data
        const processStream = async () => {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process complete SSE events (separated by double newlines)
                const events = buffer.split('\n\n');
                buffer = events.pop(); // Keep incomplete data in buffer

                for (const event of events) {
                    if (event.startsWith('data: ')) {
                        const dataStr = event.slice(6); // Remove 'data: ' prefix
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
        showToast(`分离失败: ${error.message}`, 'error');

        // Hide processing progress in now-playing card
        hideProcessingInNowPlayingCard();

        // Remove processing state from upload panel
        if (elements.uploadPanel) {
            elements.uploadPanel.classList.remove('processing');
        }

        // Restore dropzone to uploaded state (so user can retry)
        const uploadDropzone = document.querySelector('.upload-dropzone');
        if (uploadDropzone) {
            uploadDropzone.classList.remove('disabled');
            uploadDropzone.classList.add('uploaded');
        }

        // Re-enable the Process button on error
        if (elements.confirmUploadBtn) {
            elements.confirmUploadBtn.disabled = false;
            elements.confirmUploadBtn.textContent = '处理';
            elements.confirmUploadBtn.style.opacity = '1';
            elements.confirmUploadBtn.style.cursor = 'pointer';
        }
        if (elements.cancelUploadBtn) {
            elements.cancelUploadBtn.disabled = false;
        }

        // Reset processing state on error
        state.processing = false;
        state.processingType = null;
    }
}

/**
 * Handle real-time progress updates from SSE stream
 * Shows progress in now-playing card instead of uploadPanel
 */
function handleProgressUpdate(data) {
    const { stage, current, total, message, percentage, status } = data;

    // Update processing progress in now-playing card
    showProcessingInNowPlayingCard(message, percentage, current, total);

    // Log progress for debugging
    console.log(`Progress [${stage}]: ${current}/${total} - ${message}`);

    // Handle completion
    if (stage === 'complete' || status === 'success') {
        // NEW: Mark uploaded file as separated
        if (state.uploadedFile && state.uploadedFile.name) {
            state.uploadedFile.isSeparated = true;
        }

        // NEW: Keep deprecated selectedFile in sync for backward compatibility
        if (state.selectedFile) {
            state.selectedFile.isSeparated = true;
        }

        // Reset processing state
        state.processing = false;
        state.processingType = null;

        // Update UI: Show track list with success message
        updateAfterSeparation().then(() => {
            console.log('Separation completed and UI updated');
            showToast('✅ 分离完成!', 'success');
        });
    }

    // Handle error
    if (stage === 'error' || status === 'error') {
        showToast(`分离失败: ${data.message}`, 'error');

        // Hide processing progress in now-playing card
        hideProcessingInNowPlayingCard();

        // Remove processing state from upload panel
        if (elements.uploadPanel) {
            elements.uploadPanel.classList.remove('processing');
        }

        // Restore dropzone to uploaded state (so user can retry)
        const uploadDropzone = document.querySelector('.upload-dropzone');
        if (uploadDropzone) {
            uploadDropzone.classList.remove('disabled');
            uploadDropzone.classList.add('uploaded');
        }

        // Re-enable the Process button on error
        if (elements.confirmUploadBtn) {
            elements.confirmUploadBtn.disabled = false;
            elements.confirmUploadBtn.textContent = '处理';
            elements.confirmUploadBtn.style.opacity = '1';
            elements.confirmUploadBtn.style.cursor = 'pointer';
        }
        if (elements.cancelUploadBtn) {
            elements.cancelUploadBtn.disabled = false;
        }
    }
}

/**
 * Show processing progress in now-playing card
 */
function showProcessingInNowPlayingCard(message, percentage, current, total) {
    if (!elements.nowPlayingContent) return;

    const displayMessage = message || '正在处理...';
    const progressWidth = percentage !== undefined ? percentage : 0;
    const details = (current !== undefined && total !== undefined && total > 0)
        ? `进度: ${current}/${total} (${Math.round((current / total) * 100)}%)`
        : '';

    // Generate song info bar if we have an uploaded file
    let songInfoHTML = '';
    if (state.uploadedFile && state.uploadedFile.name) {
        songInfoHTML = generateSongInfoBar(state.uploadedFile);
    }

    elements.nowPlayingContent.innerHTML = `
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

    // Update header
    if (elements.nowPlayingHeader) {
        elements.nowPlayingHeader.textContent = '⏳ 分离中...';
    }
}

/**
 * Hide processing progress and reset now-playing card
 */
function hideProcessingInNowPlayingCard() {
    if (!elements.nowPlayingContent) return;

    // Reset to placeholder
    elements.nowPlayingContent.innerHTML = '<div class="placeholder-text">选择音轨开始播放</div>';

    // Reset header
    if (elements.nowPlayingHeader) {
        elements.nowPlayingHeader.textContent = '🎶 现在播放';
    }
}

/**
 * Update UI after separation completes
 */
async function updateAfterSeparation() {
    // Load tracks from storage/uploaded/separated/
    await loadTracks();

    // Hide the process card (not needed anymore since tracks are separated)
    if (elements.processCard) {
        elements.processCard.classList.add('hidden');
    }

    // Show success message in now-playing card before resetting
    if (elements.nowPlayingContent) {
        // Generate song info bar if we have a selected file
        let songInfoHTML = '';
        if (state.selectedFile) {
            songInfoHTML = generateSongInfoBar(state.selectedFile, state.selectedFile.source || 'upload', 'complete');
        }

        elements.nowPlayingContent.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
                ${songInfoHTML}
                <div class="processing-content">
                    <div style="font-size: 1.25rem; font-weight: 700; color: #22c55e; margin-bottom: 12px;">
                        ✅ 分离完成!
                    </div>
                    <div style="font-size: 0.95rem; color: var(--text-secondary);">
                        分离结果已加载到音轨库
                    </div>
                </div>
            </div>
        `;
    }

    if (elements.nowPlayingHeader) {
        elements.nowPlayingHeader.textContent = '✅ 完成';
    }

    // After a brief delay, show track list with song info bar
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Hide processing progress in now-playing card
    hideProcessingInNowPlayingCard();

    // Reset now-playing header
    if (elements.nowPlayingHeader) {
        elements.nowPlayingHeader.textContent = '🎶 现在播放';
    }

    // Show track list with song info bar
    updateNowPlayingDisplay();

    // Fold upload panel (set uploadVisible to false so panel hides)
    state.uploadVisible = false;
    elements.uploadPanel.classList.add('hidden');

    // Lock the upload button (disable it)
    state.uploadLocked = true;
    if (elements.uploadBtn) {
        elements.uploadBtn.disabled = true;
        elements.uploadBtn.textContent = '+ 上传';
    }

    console.log('Upload panel folded and locked after separation');
}

/**
 * No longer needed - processing happens via separate_by_name endpoint
 */

/**
 * Update Progress UI
 */
function updateProgressUI(text, percent) {
    if (elements.progressText) {
        elements.progressText.textContent = text;
    }
    if (elements.progressPercent) {
        elements.progressPercent.textContent = `${percent}%`;
    }
    if (elements.progressFill) {
        elements.progressFill.style.width = `${percent}%`;
    }
}

/**
 * Update YouTube Progress UI
 */
function updateYouTubeProgressUI(text, percent) {
    if (elements.youtubeProgressText) {
        elements.youtubeProgressText.textContent = text;
    }
    if (elements.youtubeProgressPercent) {
        elements.youtubeProgressPercent.textContent = `${percent}%`;
    }
    const fill = elements.youtubeProgress?.querySelector('.progress-fill');
    if (fill) {
        fill.style.width = `${percent}%`;
    }
}

/**
 * Handle YouTube Download
 * Downloads to storage/uploaded/ then updates UI
 * Clears existing files before download (one file at a time)
 */
async function handleYouTubeDownload() {
    if (!state.apiConnected) {
        showToast('API 未连接', 'error');
        return;
    }

    const url = elements.youtubeUrl?.value.trim();
    if (!url) {
        showToast('请输入 YouTube 视频链接', 'warning');
        return;
    }

    // NEW: Clear existing files before YouTube download (one file at a time)
    if (state.uploadedFile && state.uploadedFile.name) {
        console.log('Clearing existing uploaded file before YouTube download:', state.uploadedFile.name);
        try {
            await fetch(`${API_BASE_URL}/separation/clear`, { method: 'POST' });
            // Clear state
            state.uploadedFile = { name: null, path: null, size: null, duration: null, source: null, timestamp: null, isSeparated: false };
            state.selectedFile = null;  // Keep deprecated field in sync
        } catch (clearError) {
            console.warn('Failed to clear existing files:', clearError);
        }
    }

    // Set processing state
    state.processing = true;
    state.processingType = 'download';

    // Show progress
    elements.youtubeProgress?.classList.remove('hidden');
    updateYouTubeProgressUI('正在下载...', 20);

    try {
        const response = await fetch(`${API_BASE_URL}/youtube/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                name: elements.youtubeName?.value.trim() || undefined,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            updateYouTubeProgressUI('下载完成!', 100);
            showToast('✅ 下载成功!', 'success');

            // Clear inputs
            if (elements.youtubeUrl) elements.youtubeUrl.value = '';
            if (elements.youtubeName) elements.youtubeName.value = '';

            // Reset processing state
            state.processing = false;
            state.processingType = null;

            // Show preview with play controls for the downloaded file
            await showYouTubePreview(result.data);

            // Hide YouTube progress after delay
            setTimeout(() => {
                elements.youtubeProgress?.classList.add('hidden');
            }, 2000);
        } else {
            throw new Error(result.message || '下载失败');
        }

    } catch (error) {
        console.error('YouTube download error:', error);
        showToast(`下载失败: ${error.message}`, 'error');
        updateYouTubeProgressUI('下载失败', 0);
        setTimeout(() => {
            elements.youtubeProgress?.classList.add('hidden');
        }, 2000);

        // Reset processing state on error
        state.processing = false;
        state.processingType = null;
    }
}

/**
 * Show YouTube download preview with play controls
 * Allows user to listen to original file before separation
 * Note: YouTube download already clears existing files before download (in handleYouTubeDownload)
 */
async function showYouTubePreview(downloadResult) {
    const filename = downloadResult.file_path.split('/').pop();
    const duration = downloadResult.duration;

    // NEW: Store in unified uploadedFile state
    state.uploadedFile = {
        name: filename,
        path: downloadResult.file_path,
        duration: duration,
        source: 'youtube',
        timestamp: Date.now(),
        isSeparated: false,
        size: downloadResult.size || 0
    };

    // NEW: Keep deprecated selectedFile in sync for backward compatibility
    state.selectedFile = {
        name: filename,
        path: downloadResult.file_path,
        duration: duration,
        source: 'youtube',
        isSeparated: false,
        size: downloadResult.size || 0
    };

    // Hide upload panel (fold it)
    state.uploadVisible = false;
    if (elements.uploadPanel) {
        elements.uploadPanel.classList.add('hidden');
    }

    // Hide process card (we're using now-playing card exclusively)
    if (elements.processCard) {
        elements.processCard.classList.add('hidden');
    }

    // Update now-playing card with preview and Separate button
    if (elements.nowPlayingContent) {
        elements.nowPlayingContent.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
                ${generateSongInfoBar(state.uploadedFile, 'youtube', 'ready')}
                <div style="display: flex; gap: 8px; margin-top: 8px;">
                    <button id="playPreviewBtn" class="btn-secondary" style="flex: 1;">▶ 播放预览</button>
                    <button id="separateBtn" class="btn-primary" style="flex: 1;">分离处理</button>
                </div>
            </div>
        `;

        // Add click handlers for the buttons
        const playPreviewBtn = document.getElementById('playPreviewBtn');
        if (playPreviewBtn) {
            playPreviewBtn.addEventListener('click', playOriginalFile);
        }

        const separateBtn = document.getElementById('separateBtn');
        if (separateBtn) {
            // Use unified processUploadedFile function
            separateBtn.addEventListener('click', processUploadedFile);
        }
    }

    // Update now-playing header
    if (elements.nowPlayingHeader) {
        elements.nowPlayingHeader.textContent = '🎵 YouTube 预览';
    }

    // Update total time display for preview
    if (elements.totalTime && duration) {
        elements.totalTime.textContent = formatTime(duration);
    }

    // Reset current time to 0:00
    if (elements.currentTime) {
        elements.currentTime.textContent = '0:00';
    }

    // Reset seek bar
    if (elements.seekBar) {
        elements.seekBar.value = 0;
    }

    // Enable play controls for original file
    state.isPlaying = false;
    updatePlayState();
}

/**
 * DEPRECATED: Use processUploadedFile() instead
 * Separate downloaded YouTube file
 * The file is in storage/uploaded/, now run separation on it
 */
async function separateYouTubeFile() {
    // DEPRECATED: Use processUploadedFile() instead
    console.warn('separateYouTubeFile() is deprecated, use processUploadedFile() instead');
    if (!state.selectedFile || !state.selectedFile.name) {
        showToast('请先下载 YouTube 音频', 'warning');
        return;
    }

    const filename = state.selectedFile.name;
    const formData = new FormData();
    formData.append('filename', filename);

    // Show processing progress in now-playing card
    showProcessingInNowPlayingCard('开始分离...', 0, 0, 0);

    // Disable the Separate button during processing
    if (elements.confirmUploadBtn) {
        elements.confirmUploadBtn.disabled = true;
        elements.confirmUploadBtn.style.opacity = '0.5';
        elements.confirmUploadBtn.style.cursor = 'not-allowed';
    }

    // Stop any currently playing audio
    if (window.originalAudioPlayer && !window.originalAudioPlayer.paused) {
        window.originalAudioPlayer.pause();
    }
    state.isPlaying = false;
    updatePlayState();

    try {
        // Use SSE endpoint for real-time progress
        const response = await fetch(`${API_BASE_URL}/separation/separate_by_name_stream`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // Check if it's a streaming response
        if (response.headers.get('content-type')?.includes('text/event-stream')) {
            // Read SSE stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n').filter(line => line.trim().startsWith('data:'));

                for (const line of lines) {
                    try {
                        const data = JSON.parse(line.replace('data:', '').trim());
                        handleProgressUpdate(data);
                    } catch (e) {
                        console.log('Parse error:', e);
                    }
                }
            }
        } else {
            // Non-streaming response
            const result = await response.json();
            if (result.status === 'success') {
                handleProgressUpdate({ stage: 'complete', status: 'success', message: '分离完成' });
            }
        }

    } catch (error) {
        console.error('YouTube separation error:', error);
        showToast(`分离失败: ${error.message}`, 'error');

        // Hide processing progress in now-playing card
        hideProcessingInNowPlayingCard();

        // Restore button state on error
        if (elements.confirmUploadBtn) {
            elements.confirmUploadBtn.disabled = false;
            elements.confirmUploadBtn.style.opacity = '1';
            elements.confirmUploadBtn.style.cursor = 'pointer';
            elements.confirmUploadBtn.textContent = '分离';
        }
    }
}

/**
 * Show Toast Notification
 */
function showToast(message, type = 'info') {
    if (!elements.toast || !elements.toastMessage) return;

    elements.toastMessage.textContent = message;
    elements.toast.className = `toast show ${type}`;

    clearTimeout(elements.toast.hideTimeout);

    elements.toast.hideTimeout = setTimeout(() => {
        elements.toast.classList.remove('show');
    }, 3000);

    // Also announce to screen readers
    announceToScreenReader(message);
}

/**
 * Announce message to screen readers via hidden live region
 * @param {string} message - Message to announce
 */
function announceToScreenReader(message) {
    if (!elements.srAnnounce) return;

    // Clear and set content to trigger announcement
    elements.srAnnounce.textContent = '';
    setTimeout(() => {
        elements.srAnnounce.textContent = message;
    }, 100);
}

/**
 * Format Time (seconds to MM:SS)
 */
function formatTime(seconds) {
    if (isNaN(seconds) || !isFinite(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Utility: Debounce
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Performance-optimized track list rendering with debouncing
 */
const debouncedRenderTrackList = debounce(renderTrackList, 150);

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
