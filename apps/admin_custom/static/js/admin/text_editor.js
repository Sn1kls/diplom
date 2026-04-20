document.addEventListener('DOMContentLoaded', function () {
    function getThemeSettings() {
        const isDark = document.documentElement.classList.contains("dark");
        return {
            isDark: isDark,
            skin: isDark ? "oxide-dark" : "oxide",
            content_css: isDark ? "dark" : "default"
        };
    }

    function renderTinyMCE() {
        if (!window.tinymce) {
            console.warn("TinyMCE not found yet...");
            return;
        }

        const theme = getThemeSettings();

        const editors = window.tinymce.editors || [];
        if (editors.length > 0) {
            for (let i = 0; i < editors.length; i++) {
                if (editors[i]) {
                    editors[i].save();
                }
            }
        }
        window.tinymce.remove();

        window.tinymce.init({
            selector: 'textarea',
            images_upload_url: '/api/admin/upload-files',
            automatic_uploads: true,
            paste_data_images: true,
            images_replace_blob_uris: true,
            images_upload_credentials: true,
            relative_urls: false,
            remove_script_host: false,
            convert_urls: true,
            theme: "silver",
            height: 400,
            width: "100%",
            menubar: "file edit view insert format tools table help",
            plugins: "advlist autolink lists link image charmap preview anchor searchreplace visualblocks code fullscreen insertdatetime media table code help wordcount codesample directionality visualchars pagebreak",
            toolbar: "undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | alignleft aligncenter alignright alignjustify | outdent indent | numlist bullist | forecolor backcolor removeformat | charmap emoticons | link anchor image media codesample pagebreak | ltr rtl | fullscreen preview code",
            branding: false,
            promotion: false,
            license_key: "gpl",
            help_accessibility: false,
            elementpath: false,
            skin: theme.skin,
            content_css: theme.content_css,

            images_upload_handler: (blobInfo, progress) => new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.withCredentials = true;
                xhr.open('POST', '/api/admin/upload-files');

                const getCookie = (name) => {
                    let cookieValue = null;
                    if (document.cookie && document.cookie !== '') {
                        const cookies = document.cookie.split(';');
                        for (let i = 0; i < cookies.length; i++) {
                            const cookie = cookies[i].trim();
                            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                                break;
                            }
                        }
                    }
                    return cookieValue;
                };

                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));

                xhr.upload.onprogress = (e) => {
                    progress(e.loaded / e.total * 100);
                };

                xhr.onload = function() {
                    if (xhr.status < 200 || xhr.status >= 300) {
                        reject({ message: 'HTTP Error: ' + xhr.status, remove: true });
                        return;
                    }
                    const json = JSON.parse(xhr.responseText);
                    console.log("URL from server:", json.location);

                    if (!json || typeof json.location !== 'string') {
                        reject({ message: 'Invalid JSON: ' + xhr.responseText, remove: true });
                        return;
                    }

                    resolve(json.location);
                };

                xhr.onerror = function () {
                    reject({ message: 'Image upload failed due to a network error.', remove: true });
                };

                const formData = new FormData();
                formData.append('file', blobInfo.blob(), blobInfo.filename());
                xhr.send(formData);
            }),

            setup: function(editor) {
                editor.on('init', function() {
                    const body = editor.getBody();
                    if (theme.isDark) {
                        body.style.backgroundColor = "#111827";
                        body.style.color = "#f3f4f6";
                    } else {
                        body.style.backgroundColor = "#ffffff";
                        body.style.color = "#000000";
                    }
                });
            }
        });
    }

    const observer = new MutationObserver((mutations) => {
        const classChanged = mutations.some(m => m.attributeName === 'class');
        if (classChanged) {
            renderTinyMCE();
        }
    });

    observer.observe(document.documentElement, { attributes: true });

    setTimeout(renderTinyMCE, 1);
});