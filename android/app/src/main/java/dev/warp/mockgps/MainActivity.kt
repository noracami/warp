package dev.warp.mockgps

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import java.net.Inet4Address
import java.net.NetworkInterface

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var ipText: TextView
    private lateinit var locationText: TextView
    private lateinit var lastTeleportText: TextView

    private val handler = Handler(Looper.getMainLooper())
    private val refresh = object : Runnable {
        override fun run() {
            updateStatus()
            handler.postDelayed(this, 1000L)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContentView(R.layout.activity_main)

        val root = findViewById<ViewGroup>(R.id.rootContainer)
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }

        statusText = findViewById(R.id.statusText)
        ipText = findViewById(R.id.ipText)
        locationText = findViewById(R.id.locationText)
        lastTeleportText = findViewById(R.id.lastTeleportText)

        findViewById<Button>(R.id.openDevOptionsButton).setOnClickListener { openDeveloperOptions() }
        findViewById<Button>(R.id.stopMockButton).setOnClickListener { stopMock() }
        findViewById<Button>(R.id.copyIpButton).setOnClickListener { copyIpToClipboard() }

        requestPermissionsIfNeeded()
        bootService()
    }

    override fun onResume() {
        super.onResume()
        handler.post(refresh)
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(refresh)
    }

    private fun bootService() {
        val intent = Intent(this, MockLocationService::class.java).apply {
            action = MockLocationService.ACTION_BOOT
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopMock() {
        val intent = Intent(this, MockLocationService::class.java).apply {
            action = MockLocationService.ACTION_STOP
        }
        startService(intent)
    }

    private fun copyIpToClipboard() {
        val url = buildServerUrl() ?: run {
            Toast.makeText(this, "尚未連上網路", Toast.LENGTH_SHORT).show()
            return
        }
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("Warp URL", url))
        Toast.makeText(this, "已複製：$url", Toast.LENGTH_SHORT).show()
    }

    private fun openDeveloperOptions() {
        val intents = listOf(
            Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS),
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                .setData(Uri.parse("package:$packageName")),
        )
        for (intent in intents) {
            try {
                startActivity(intent)
                return
            } catch (_: ActivityNotFoundException) {
            }
        }
        Toast.makeText(this, "無法開啟開發者選項，請手動前往設定", Toast.LENGTH_LONG).show()
    }

    private fun requestPermissionsIfNeeded() {
        val needed = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED) {
            needed += Manifest.permission.ACCESS_FINE_LOCATION
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
                needed += Manifest.permission.POST_NOTIFICATIONS
            }
        }
        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), 1)
        }
    }

    private fun updateStatus() {
        val running = MockLocationService.isRunning
        statusText.text = if (running) "● Running" else "○ Waiting"

        ipText.text = buildServerUrl() ?: "尚未連上網路"

        val loc = MockLocationService.currentLocation
        locationText.text = if (loc != null) {
            "lat = ${loc.first}\nlng = ${loc.second}"
        } else "—"

        val lastAt = MockLocationService.lastTeleportAt
        lastTeleportText.text = if (lastAt > 0) {
            val elapsed = (System.currentTimeMillis() - lastAt) / 1000
            when {
                elapsed < 60 -> "${elapsed}s ago"
                elapsed < 3600 -> "${elapsed / 60}m ago"
                else -> "${elapsed / 3600}h ago"
            }
        } else "—"
    }

    private fun buildServerUrl(): String? {
        val ip = getLocalIp() ?: return null
        return "http://$ip:${HttpServer.DEFAULT_PORT}"
    }

    private fun getLocalIp(): String? {
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces() ?: return null
            for (intf in interfaces) {
                if (intf.isLoopback || !intf.isUp) continue
                for (addr in intf.inetAddresses) {
                    if (!addr.isLoopbackAddress && addr is Inet4Address) {
                        return addr.hostAddress
                    }
                }
            }
        } catch (_: Exception) {
        }
        return null
    }
}
