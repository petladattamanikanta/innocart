package io.innocart.companion;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(SessionInitiationPlugin.class);
        super.onCreate(savedInstanceState);
    }
}

