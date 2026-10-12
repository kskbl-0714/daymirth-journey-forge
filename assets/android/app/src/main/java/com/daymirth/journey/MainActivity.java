package com.daymirth.journey;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import android.widget.LinearLayout;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/** Local asset origin isolates native bridge from arbitrary network documents. */
public class MainActivity extends Activity {
    private static final String ORIGIN = "https://appassets.androidplatform.net/";
    private WebView web;
    private ValueCallback<Uri[]> chooser;
    private String language = "en";
    private String allowedTickets = "[]";
    private String pendingBackup;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        try (InputStream in = getAssets().open("www/trip.json")) {
            JSONObject trip = new JSONObject(new String(read(in), StandardCharsets.UTF_8));
            language = trip.getJSONObject("app").optString("language", "en");
            allowedTickets = trip.optJSONArray("tickets").toString();
        } catch (Exception ignored) { }
        web = new WebView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(), insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        root.addView(web, new LinearLayout.LayoutParams(-1, -1));
        setContentView(root);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(true);
        web.getSettings().setSupportMultipleWindows(true);
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (!uri.toString().startsWith(ORIGIN)) return null;
                try {
                    String path = uri.getPath().substring(1);
                    if (path.isEmpty()) path = "index.html";
                    if (path.contains("\\") || path.contains("%")) throw new Exception("Invalid path");
                    for (String segment : path.split("/")) if (segment.equals(".") || segment.equals("..")) throw new Exception("Invalid path");
                    String mime = path.endsWith(".html") ? "text/html" : path.endsWith(".js") ? "application/javascript" : path.endsWith(".css") ? "text/css" : path.endsWith(".json") ? "application/json" : path.endsWith(".svg") ? "image/svg+xml" : path.endsWith(".png") ? "image/png" : path.endsWith(".webp") ? "image/webp" : path.endsWith(".pdf") ? "application/pdf" : path.endsWith(".webmanifest") ? "application/manifest+json" : "image/jpeg";
                    return new WebResourceResponse(mime, "UTF-8", getAssets().open("www/" + path));
                } catch (Exception e) {
                    return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", null, new ByteArrayInputStream(new byte[0]));
                }
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (request.getUrl().toString().startsWith(ORIGIN)) return false;
                external(request.getUrl()); return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (chooser != null) chooser.onReceiveValue(null);
                chooser = callback;
                Intent intent = params.createIntent();
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                try { startActivityForResult(intent, 100); return true; }
                catch (Exception e) { chooser = null; return false; }
            }
            @Override public boolean onCreateWindow(WebView view, boolean dialog, boolean gesture, android.os.Message message) {
                if (!gesture) return false;
                WebView child = new WebView(MainActivity.this);
                child.setWebViewClient(new WebViewClient() {
                    @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) { external(r.getUrl()); v.destroy(); return true; }
                });
                ((WebView.WebViewTransport) message.obj).setWebView(child); message.sendToTarget(); return true;
            }
        });
        web.addJavascriptInterface(new TicketBridge(), "AndroidTickets");
        web.loadUrl(ORIGIN + "index.html");
    }
    private void external(Uri uri) {
        if (!"https".equals(uri.getScheme())) return;
        try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); }
        catch (Exception e) { Toast.makeText(this, "No compatible app found", Toast.LENGTH_SHORT).show(); }
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == 100 && chooser != null) { chooser.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result, data)); chooser = null; }
        if (request == 101 && pendingBackup != null) {
            String backup = pendingBackup; pendingBackup = null;
            if (result == RESULT_OK && data != null && data.getData() != null) {
                try (OutputStream out = getContentResolver().openOutputStream(data.getData())) {
                    if (out == null) throw new Exception("No output stream");
                    out.write(backup.getBytes(StandardCharsets.UTF_8));
                    Toast.makeText(this, "en".equals(language) ? "Backup exported" : "备份已导出", Toast.LENGTH_SHORT).show();
                } catch (Exception e) { Toast.makeText(this, "en".equals(language) ? "Export failed; try again" : "导出失败，请重试", Toast.LENGTH_LONG).show(); }
            }
        }
    }
    @Override public void onBackPressed() {
        web.evaluateJavascript("(()=>{const d=document.querySelector('dialog[open]');if(d){d.close();return true;}return false;})()", value -> { if (!"true".equals(value)) { if (web.canGoBack()) web.goBack(); else MainActivity.super.onBackPressed(); } });
    }
    private static byte[] read(InputStream in) throws Exception { ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] b = new byte[8192]; int n; while ((n = in.read(b)) >= 0) out.write(b, 0, n); return out.toByteArray(); }
    private class TicketBridge {
        @JavascriptInterface public void saveRecords(String json, String filename) {
            try {
                JSONObject backup = new JSONObject(json);
                if (backup.getInt("schemaVersion") != 1 || !filename.matches("[a-z0-9-]+-records\\.json")) return;
                backup.getJSONObject("records");
                new Handler(Looper.getMainLooper()).post(() -> {
                    if (pendingBackup != null) return;
                    pendingBackup = json;
                    Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE); intent.setType("application/json"); intent.putExtra(Intent.EXTRA_TITLE, filename);
                    try { startActivityForResult(intent, 101); }
                    catch (Exception e) { pendingBackup = null; Toast.makeText(MainActivity.this, "No compatible file picker found", Toast.LENGTH_SHORT).show(); }
                });
            } catch (Exception ignored) { }
        }
        @JavascriptInterface public void open(String json) {
            try {
                JSONArray requested = new JSONArray(json), allowed = new JSONArray(allowedTickets);
                if (requested.length() == 0) return;
                for (int i=0; i<requested.length(); i++) {
                    String file = requested.getJSONObject(i).getString("file");
                    if (!file.matches("tickets/[A-Za-z0-9_.-]+\\.(pdf|png|jpg|jpeg)")) return;
                    boolean found = false;
                    for (int j=0; j<allowed.length(); j++) if (file.equals(allowed.getJSONObject(j).optString("file"))) found = true;
                    if (!found) return;
                }
                new Handler(Looper.getMainLooper()).post(() -> {
                    Intent intent = new Intent(MainActivity.this, TicketViewerActivity.class);
                    intent.putExtra("tickets", json); intent.putExtra("language", language); startActivity(intent);
                });
            } catch (Exception ignored) { }
        }
    }
}
