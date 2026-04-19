package dev.warp.mockgps

import android.app.AppOpsManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.location.Location
import android.location.LocationManager
import android.location.provider.ProviderProperties
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Process
import android.os.SystemClock
import android.util.Log
import androidx.core.app.NotificationCompat

class MockLocationService : Service() {

    companion object {
        const val CHANNEL_ID = "mock_gps"
        const val NOTIF_ID = 1
        const val ACTION_BOOT = "dev.warp.mockgps.internal.BOOT"
        const val ACTION_START = "dev.warp.mockgps.internal.START"
        const val ACTION_STOP = "dev.warp.mockgps.internal.STOP"
        const val EXTRA_LAT = "lat"
        const val EXTRA_LNG = "lng"

        private const val TAG = "MockLocationService"

        private val PROVIDERS = listOf(
            LocationManager.GPS_PROVIDER,
            LocationManager.NETWORK_PROVIDER,
        )

        @Volatile var isRunning: Boolean = false
        @Volatile var currentLocation: Pair<Double, Double>? = null
        @Volatile var lastTeleportAt: Long = 0L
        @Volatile var mockReady: Boolean = false
    }

    private lateinit var locationManager: LocationManager
    private val handler = Handler(Looper.getMainLooper())
    private var isForegroundStarted = false
    private var httpServer: HttpServer? = null

    private val pushRunnable = object : Runnable {
        override fun run() {
            pushMockLocation()
            handler.postDelayed(this, 500L)
        }
    }

    override fun onCreate() {
        super.onCreate()
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        createChannel()
        setupProviders()
        startHttpServer()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_BOOT -> handleBoot()
            ACTION_START -> handleStart(intent)
            ACTION_STOP -> handleStop()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacks(pushRunnable)
        stopHttpServer()
        tearDownProviders()
        isRunning = false
        currentLocation = null
        isForegroundStarted = false
    }

    private fun handleBoot() {
        ensureForeground(buildWaitingNotification())
    }

    private fun handleStart(intent: Intent) {
        val lat = intent.getDoubleExtra(EXTRA_LAT, Double.NaN)
        val lng = intent.getDoubleExtra(EXTRA_LNG, Double.NaN)
        if (lat.isNaN() || lng.isNaN()) return
        currentLocation = lat to lng
        lastTeleportAt = System.currentTimeMillis()

        ensureForeground(buildRunningNotification(lat, lng))
        if (!isRunning) {
            isRunning = true
            handler.post(pushRunnable)
        }
    }

    private fun handleStop() {
        handler.removeCallbacks(pushRunnable)
        currentLocation = null
        isRunning = false
        if (isForegroundStarted) {
            val mgr = getSystemService(NotificationManager::class.java)
            mgr.notify(NOTIF_ID, buildWaitingNotification())
        }
    }

    private fun ensureForeground(notif: Notification) {
        if (!isForegroundStarted) {
            startForegroundCompat(notif)
            isForegroundStarted = true
        } else {
            val mgr = getSystemService(NotificationManager::class.java)
            mgr.notify(NOTIF_ID, notif)
        }
    }

    private fun startHttpServer() {
        if (httpServer != null) return
        try {
            httpServer = HttpServer(this).apply { start() }
            Log.i(TAG, "HTTP server started on port ${HttpServer.DEFAULT_PORT}")
        } catch (e: Exception) {
            Log.e(TAG, "failed to start HTTP server", e)
        }
    }

    private fun stopHttpServer() {
        httpServer?.stop()
        httpServer = null
    }

    private fun isSelectedAsMockProvider(): Boolean {
        return try {
            val appOps = getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
            val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                appOps.unsafeCheckOpNoThrow(
                    AppOpsManager.OPSTR_MOCK_LOCATION,
                    Process.myUid(),
                    packageName,
                )
            } else {
                @Suppress("DEPRECATION")
                appOps.checkOp(
                    AppOpsManager.OPSTR_MOCK_LOCATION,
                    Process.myUid(),
                    packageName,
                )
            }
            mode == AppOpsManager.MODE_ALLOWED
        } catch (e: Exception) {
            Log.w(TAG, "failed to check mock location appop", e)
            false
        }
    }

    @Synchronized
    private fun setupProviders() {
        if (!isSelectedAsMockProvider()) {
            Log.w(TAG, "this app is not selected as mock location provider")
            mockReady = false
            return
        }
        var ok = true
        for (p in PROVIDERS) {
            try {
                if (locationManager.getProvider(p) != null) {
                    try { locationManager.removeTestProvider(p) } catch (_: Exception) {}
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    locationManager.addTestProvider(
                        p,
                        false, false, false, false, true, true, true,
                        ProviderProperties.POWER_USAGE_LOW,
                        ProviderProperties.ACCURACY_FINE,
                    )
                } else {
                    @Suppress("DEPRECATION")
                    locationManager.addTestProvider(
                        p, false, false, false, false, true, true, true, 1, 1,
                    )
                }
                locationManager.setTestProviderEnabled(p, true)
            } catch (e: SecurityException) {
                ok = false
                Log.w(TAG, "not selected as mock provider for $p")
            } catch (e: Exception) {
                ok = false
                Log.w(TAG, "failed to setup provider $p", e)
            }
        }
        mockReady = ok
    }

    @Synchronized
    fun retrySetupIfNeeded() {
        if (!mockReady) setupProviders()
    }

    private fun tearDownProviders() {
        for (p in PROVIDERS) {
            try {
                locationManager.setTestProviderEnabled(p, false)
                locationManager.removeTestProvider(p)
            } catch (_: Exception) {}
        }
        mockReady = false
    }

    private fun pushMockLocation() {
        val (lat, lng) = currentLocation ?: return
        for (p in PROVIDERS) {
            val loc = Location(p).apply {
                latitude = lat
                longitude = lng
                accuracy = 1.0f
                altitude = 0.0
                time = System.currentTimeMillis()
                elapsedRealtimeNanos = SystemClock.elapsedRealtimeNanos()
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    bearingAccuracyDegrees = 0.1f
                    verticalAccuracyMeters = 0.1f
                    speedAccuracyMetersPerSecond = 0.01f
                }
            }
            try {
                locationManager.setTestProviderLocation(p, loc)
            } catch (_: Exception) {}
        }
    }

    private fun startForegroundCompat(notif: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notif, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } else {
            startForeground(NOTIF_ID, notif)
        }
    }

    private fun createChannel() {
        val mgr = getSystemService(NotificationManager::class.java)
        val ch = NotificationChannel(CHANNEL_ID, "Mock GPS", NotificationManager.IMPORTANCE_LOW)
        mgr.createNotificationChannel(ch)
    }

    private fun buildWaitingNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Mock GPS · Waiting")
            .setContentText("HTTP server :${HttpServer.DEFAULT_PORT}")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .build()
    }

    private fun buildRunningNotification(lat: Double, lng: Double): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Mock GPS · Running")
            .setContentText("lat=$lat  lng=$lng")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .build()
    }
}
