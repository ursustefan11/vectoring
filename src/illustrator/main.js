app.preferences.setBooleanPreference("ShowExternalJSXWarning", false)

var filePath = "C:/Users/ursus/Downloads/test.png";
traceImage(filePath);

function traceImage(filePath) {
    var doc = app.documents.add();
    var placedItem = doc.placedItems.add();

    placedItem.file = new File(filePath);

    // Wait for the file to be placed before tracing
    app.redraw();

    // Trace the image
    var tracingOptions = {
        ignoreWhite: true
    };
    placedItem.trace(tracingOptions);

    // Apply the options and redraw the document
    app.redraw();
}