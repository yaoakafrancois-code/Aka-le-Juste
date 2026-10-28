package ci.cacaocoop.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.print.PrintAttributes;
import android.print.PrintManager;
import android.text.InputType;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.Menu;
import android.view.MenuItem;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Application CacaoCoop pour tablettes et smartphones Android.
 *
 * Elle affiche le logiciel servi par l'ordinateur de la coopérative (réseau Wi-Fi local) ou par le serveur web.
 * Les pesées de la page « Collecte terrain » sont gardées sur l'appareil quand le réseau est coupé, puis envoyées
 * automatiquement à son retour.
 */
public class MainActivity extends Activity {

    private static final String PREFS = "cacaocoop";
    private static final String CLE_SERVEUR = "serveur";
    private static final int CHOIX_FICHIER = 1;

    private WebView vue;
    private ValueCallback<Uri[]> rappelFichier;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle etat) {
        super.onCreate(etat);
        prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String serveur = prefs.getString(CLE_SERVEUR, "");
        if (serveur.isEmpty()) {
            afficherConfiguration(null);
        } else {
            afficherLogiciel(serveur, etat);
        }
    }

    // ----- Écran de configuration : adresse du serveur -----------------------------------------------

    private void afficherConfiguration(String message) {
        vue = null;
        LinearLayout ecran = new LinearLayout(this);
        ecran.setOrientation(LinearLayout.VERTICAL);
        ecran.setGravity(Gravity.CENTER_HORIZONTAL);
        int marge = dp(24);
        ecran.setPadding(marge, marge, marge, marge);

        TextView titre = new TextView(this);
        titre.setText("CacaoCoop");
        titre.setTextSize(28);
        titre.setTextColor(Color.rgb(62, 38, 25));
        titre.setGravity(Gravity.CENTER);
        ecran.addView(titre);

        TextView aide = new TextView(this);
        aide.setText("Adresse du logiciel de la coopérative.\n\nSur l'ordinateur principal, lancez « CacaoCoop - réseau "
                + "(tablettes) » : l'adresse s'affiche dans la fenêtre (par exemple 192.168.1.10:8000).\n"
                + "La tablette doit être connectée au même Wi-Fi.");
        aide.setTextSize(16);
        aide.setPadding(0, dp(16), 0, dp(16));
        ecran.addView(aide);

        if (message != null) {
            TextView erreur = new TextView(this);
            erreur.setText(message);
            erreur.setTextColor(Color.rgb(178, 59, 59));
            erreur.setTextSize(16);
            erreur.setPadding(0, 0, 0, dp(12));
            ecran.addView(erreur);
        }

        final EditText saisie = new EditText(this);
        saisie.setHint("192.168.1.10:8000");
        saisie.setText(prefs.getString(CLE_SERVEUR, "").replace("http://", ""));
        saisie.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        saisie.setImeOptions(EditorInfo.IME_ACTION_GO);
        saisie.setSingleLine(true);
        saisie.setTextSize(20);
        ecran.addView(saisie, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        Button connecter = new Button(this);
        connecter.setText("Se connecter");
        connecter.setTextSize(18);
        connecter.setOnClickListener(v -> enregistrerServeur(saisie.getText().toString()));
        saisie.setOnEditorActionListener((v, action, ev) -> {
            enregistrerServeur(saisie.getText().toString());
            return true;
        });
        LinearLayout.LayoutParams parametres = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        parametres.topMargin = dp(16);
        ecran.addView(connecter, parametres);

        setContentView(ecran);
    }

    private void enregistrerServeur(String texte) {
        String adresse = normaliser(texte);
        if (adresse == null) {
            Toast.makeText(this, "Adresse invalide", Toast.LENGTH_LONG).show();
            return;
        }
        prefs.edit().putString(CLE_SERVEUR, adresse).apply();
        afficherLogiciel(adresse, null);
    }

    /** « 192.168.1.10 » → « http://192.168.1.10:8000 » ; une adresse complète est gardée telle quelle. */
    static String normaliser(String texte) {
        String a = texte.trim();
        if (a.isEmpty()) return null;
        while (a.endsWith("/")) a = a.substring(0, a.length() - 1);
        if (!a.startsWith("http://") && !a.startsWith("https://")) {
            a = "http://" + a;
            String hote = a.substring("http://".length());
            if (!hote.contains(":") && !hote.contains("/")) a = a + ":8000";
        }
        return URLUtil.isNetworkUrl(a) ? a : null;
    }

    // ----- Logiciel dans une WebView -------------------------------------------------------------------

    private void afficherLogiciel(final String serveur, Bundle etat) {
        vue = new WebView(this);
        WebSettings reglages = vue.getSettings();
        reglages.setJavaScriptEnabled(true);
        reglages.setDomStorageEnabled(true);  // pesées hors ligne (localStorage)
        reglages.setDatabaseEnabled(true);
        reglages.setCacheMode(WebSettings.LOAD_DEFAULT);
        reglages.setBuiltInZoomControls(true);
        reglages.setDisplayZoomControls(false);
        reglages.setUserAgentString(reglages.getUserAgentString() + " CacaoCoopAndroid/" + versionApp());
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(vue, false);

        vue.addJavascriptInterface(new Impression(), "CacaoCoopAndroid");
        vue.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest requete) {
                Uri uri = requete.getUrl();
                if (uri.getHost() != null && uri.getHost().equals(Uri.parse(serveur).getHost())) return false;
                // Liens externes (téléphone, cartes…) : application du système.
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (Exception ignore) {
                    // aucune application pour ce lien
                }
                return true;
            }

            @Override
            public void onPageStarted(WebView v, String url, Bitmap icone) {
                setTitle("CacaoCoop");
            }

            @Override
            public void onPageFinished(WebView v, String url) {
                // window.print() n'existe pas dans une WebView : on le relie à l'impression Android.
                v.evaluateJavascript("window.print = function () { CacaoCoopAndroid.imprimer(document.title); };", null);
                CookieManager.getInstance().flush();
            }

            @Override
            public void onReceivedError(WebView v, WebResourceRequest requete, WebResourceError erreur) {
                if (requete.isForMainFrame()) {
                    String page = "<html><head><meta name='viewport' content='width=device-width'></head>"
                            + "<body style='font-family:sans-serif;padding:24px;color:#2b2522'>"
                            + "<h2 style='color:#3e2619'>Serveur injoignable</h2>"
                            + "<p>Impossible de joindre <b>" + TextUtils.htmlEncode(serveur) + "</b>.</p><ul>"
                            + "<li>La tablette est-elle connectée au Wi-Fi de la coopérative ?</li>"
                            + "<li>CacaoCoop est-il lancé sur l'ordinateur avec « réseau (tablettes) » ?</li></ul>"
                            + "<p>Les pesées déjà saisies dans la collecte terrain restent sur la tablette.</p>"
                            + "<p><a href='" + TextUtils.htmlEncode(requete.getUrl().toString())
                            + "' style='font-size:18px'>Réessayer</a></p>"
                            + "<p>Menu ⋮ → « Adresse du serveur » pour la modifier.</p></body></html>";
                    v.loadDataWithBaseURL(null, page, "text/html", "UTF-8", requete.getUrl().toString());
                }
            }
        });
        vue.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> rappel, FileChooserParams params) {
                if (rappelFichier != null) rappelFichier.onReceiveValue(null);
                rappelFichier = rappel;
                try {
                    startActivityForResult(params.createIntent(), CHOIX_FICHIER);
                } catch (Exception e) {
                    rappelFichier = null;
                    Toast.makeText(MainActivity.this, "Aucune application pour choisir un fichier", Toast.LENGTH_LONG).show();
                    return false;
                }
                return true;
            }

            @Override
            public void onReceivedTitle(WebView v, String titre) {
                if (titre != null && !titre.startsWith("http")) setTitle(titre);
            }
        });
        vue.setDownloadListener((url, agent, disposition, type, taille) -> telecharger(url, agent, disposition, type));

        setContentView(vue);
        if (etat != null) {
            vue.restoreState(etat);
        } else {
            vue.loadUrl(serveur + "/");
        }
    }

    /** Exports CSV, pièces justificatives : enregistrés dans « Téléchargements ». */
    private void telecharger(String url, String agent, String disposition, String type) {
        try {
            String nom = URLUtil.guessFileName(url, disposition, type);
            DownloadManager.Request requete = new DownloadManager.Request(Uri.parse(url));
            requete.addRequestHeader("Cookie", CookieManager.getInstance().getCookie(url));
            requete.addRequestHeader("User-Agent", agent);
            requete.setMimeType(type);
            requete.setTitle(nom);
            requete.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            requete.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, nom);
            ((DownloadManager) getSystemService(DOWNLOAD_SERVICE)).enqueue(requete);
            Toast.makeText(this, "Téléchargement : " + nom, Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "Téléchargement impossible", Toast.LENGTH_LONG).show();
        }
    }

    /** Pont JavaScript → impression Android (reçus, bons de pesée, connaissements). */
    private class Impression {
        @JavascriptInterface
        public void imprimer(final String titre) {
            runOnUiThread(() -> {
                if (vue == null) return;
                PrintManager gestionnaire = (PrintManager) getSystemService(Context.PRINT_SERVICE);
                String nom = (titre == null || titre.isEmpty()) ? "CacaoCoop" : titre;
                gestionnaire.print(nom, vue.createPrintDocumentAdapter(nom),
                        new PrintAttributes.Builder().setMediaSize(PrintAttributes.MediaSize.ISO_A4).build());
            });
        }
    }

    @Override
    protected void onActivityResult(int code, int resultat, Intent donnees) {
        if (code == CHOIX_FICHIER && rappelFichier != null) {
            rappelFichier.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultat, donnees));
            rappelFichier = null;
            return;
        }
        super.onActivityResult(code, resultat, donnees);
    }

    @Override
    protected void onSaveInstanceState(Bundle etat) {
        super.onSaveInstanceState(etat);
        if (vue != null) vue.saveState(etat);
    }

    @Override
    protected void onPause() {
        super.onPause();
        CookieManager.getInstance().flush();
    }

    @Override
    public boolean onKeyDown(int touche, KeyEvent evenement) {
        if (touche == KeyEvent.KEYCODE_BACK && vue != null && vue.canGoBack()) {
            vue.goBack();
            return true;
        }
        return super.onKeyDown(touche, evenement);
    }

    // ----- Menu -----------------------------------------------------------------------------------------

    private static final int MENU_ACCUEIL = 1, MENU_TERRAIN = 2, MENU_RECHARGER = 3, MENU_SERVEUR = 4;

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        menu.add(0, MENU_ACCUEIL, 0, "Tableau de bord");
        menu.add(0, MENU_TERRAIN, 1, "Collecte terrain");
        menu.add(0, MENU_RECHARGER, 2, "Recharger la page");
        menu.add(0, MENU_SERVEUR, 3, "Adresse du serveur");
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        String serveur = prefs.getString(CLE_SERVEUR, "");
        switch (item.getItemId()) {
            case MENU_ACCUEIL:
                if (vue != null) vue.loadUrl(serveur + "/");
                return true;
            case MENU_TERRAIN:
                if (vue != null) vue.loadUrl(serveur + "/achats/terrain/");
                return true;
            case MENU_RECHARGER:
                if (vue != null) vue.reload();
                return true;
            case MENU_SERVEUR:
                new AlertDialog.Builder(this)
                        .setTitle("Adresse du serveur")
                        .setMessage("Adresse actuelle : " + serveur + "\n\nLes pesées en attente sont conservées si "
                                + "vous revenez ensuite à la même adresse.")
                        .setPositiveButton("Modifier", (d, w) -> afficherConfiguration(null))
                        .setNegativeButton("Annuler", null)
                        .show();
                return true;
            default:
                return super.onOptionsItemSelected(item);
        }
    }

    private String versionApp() {
        try {
            return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "?";
        }
    }

    private int dp(int valeur) {
        return Math.round(valeur * getResources().getDisplayMetrics().density);
    }
}
