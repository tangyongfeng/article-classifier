// 通用 JavaScript 功能

$(document).ready(function() {
    // 分类树折叠功能
    $('.category-link').on('click', function(e) {
        const $item = $(this).closest('.category-item');
        const $children = $item.find('> .category-children');

        if ($children.length > 0 && e.target === this) {
            e.preventDefault();
            $children.slideToggle(200);

            // 切换图标
            const $icon = $(this).find('i.bi-folder-fill, i.bi-folder2-open');
            if ($icon.hasClass('bi-folder-fill')) {
                $icon.removeClass('bi-folder-fill').addClass('bi-folder2-open');
            } else {
                $icon.removeClass('bi-folder2-open').addClass('bi-folder-fill');
            }
        }
    });

    // 搜索框自动聚焦（仅在搜索页）
    if (window.location.pathname === '/search') {
        $('input[name="q"]').focus();
    }

    // 文章内容中的表格添加 Bootstrap 样式
    $('.article-content table').addClass('table table-bordered table-striped');

    // 返回顶部按钮
    const $backToTop = $('<button>')
        .attr('id', 'backToTop')
        .addClass('btn btn-primary')
        .css({
            'position': 'fixed',
            'bottom': '20px',
            'right': '20px',
            'display': 'none',
            'z-index': 1000,
            'border-radius': '50%',
            'width': '50px',
            'height': '50px'
        })
        .html('<i class="bi bi-arrow-up"></i>')
        .appendTo('body');

    $(window).scroll(function() {
        if ($(this).scrollTop() > 200) {
            $backToTop.fadeIn();
        } else {
            $backToTop.fadeOut();
        }
    });

    $backToTop.click(function() {
        $('html, body').animate({ scrollTop: 0 }, 500);
    });

    // 提示框自动关闭
    setTimeout(function() {
        $('.alert').not('.alert-permanent').fadeOut();
    }, 5000);
});

// 格式化日期
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

// 复制文本到剪贴板
function copyToClipboard(text) {
    const $temp = $('<textarea>');
    $('body').append($temp);
    $temp.val(text).select();
    document.execCommand('copy');
    $temp.remove();

    // 显示提示
    showNotification('已复制到剪贴板', 'success');
}

// 显示通知
function showNotification(message, type = 'info') {
    const $notification = $('<div>')
        .addClass(`alert alert-${type} alert-dismissible fade show`)
        .css({
            'position': 'fixed',
            'top': '20px',
            'right': '20px',
            'z-index': 9999,
            'min-width': '300px'
        })
        .html(`
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `)
        .appendTo('body');

    setTimeout(function() {
        $notification.fadeOut(function() {
            $(this).remove();
        });
    }, 3000);
}
