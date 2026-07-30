package io.innocart.companion;

import android.content.Intent;
import android.net.Uri;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

@CapacitorPlugin(name = "SessionInitiation")
public class SessionInitiationPlugin extends Plugin {

    @PluginMethod
    public void initiateSession(PluginCall call) {
        String sessionId = call.getString("session_id", "IC-042");
        String userId = call.getString("user_id", "");
        String name = call.getString("name", "Shopper");
        String facialHex = call.getString("facial_hex", "#D4A373");
        String undertoneLabel = call.getString("undertone_label", "Warm-Golden");
        String backendUrl = call.getString("backend_url", "https://innocart-backend.onrender.com");

        new Thread(() -> {
            try {
                URL url = new URL(backendUrl + "/api/cart/sync-profile");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json; utf-8");
                conn.setRequestProperty("Accept", "application/json");
                conn.setDoOutput(true);

                String jsonInputString = String.format(
                    "{\"session_id\":\"%s\",\"user_id\":\"%s\",\"name\":\"%s\",\"facial_hex\":\"%s\",\"undertone_label\":\"%s\"}",
                    sessionId, userId, name, facialHex, undertoneLabel
                );

                try (OutputStream os = conn.getOutputStream()) {
                    byte[] input = jsonInputString.getBytes("utf-8");
                    os.write(input, 0, input.length);
                }

                int code = conn.getResponseCode();
                JSObject ret = new JSObject();
                ret.put("status_code", code);
                ret.put("session_id", sessionId);

                if (code == 200 || code == 201) {
                    ret.put("success", true);
                    ret.put("message", "Session successfully initiated for cart " + sessionId);
                    call.resolve(ret);
                } else {
                    ret.put("success", false);
                    ret.put("message", "Backend responded with HTTP " + code);
                    call.reject("Session initiation failed with code " + code);
                }
            } catch (Exception e) {
                JSObject ret = new JSObject();
                ret.put("success", false);
                ret.put("error", e.getMessage());
                call.reject("Network or plugin error: " + e.getMessage(), e);
            }
        }).start();
    }

    @PluginMethod
    public void getLaunchSession(PluginCall call) {
        Intent intent = getActivity().getIntent();
        Uri data = intent.getData();

        JSObject ret = new JSObject();
        if (data != null) {
            String cartId = data.getQueryParameter("cart_id");
            if (cartId == null && data.getPathSegments().size() > 1) {
                cartId = data.getLastPathSegment();
            }
            ret.put("has_deep_link", true);
            ret.put("cart_id", cartId != null ? cartId : "IC-042");
            ret.put("uri", data.toString());
        } else {
            ret.put("has_deep_link", false);
            ret.put("cart_id", null);
        }
        call.resolve(ret);
    }
}
