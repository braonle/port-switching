function relocate(url)
{
    location.href = url;
}

function confirm_delrt(url, rt, id)
{
    if (confirm("Are you sure to delete router " + rt))
    {
        delete_rt(url, rt);
        document.getElementById(id).outerHTML = ''
    }
}

function confirm_delsw(url, sw, id)
{
    if (confirm("Are you sure to delete switching rule " + sw))
    {
        delete_sw(url, sw);
        document.getElementById(id).outerHTML = ''
    }
}

function delete_rt(url, rt)
{
    var xhr = new XMLHttpRequest();

    var params = 'router=' + encodeURIComponent(rt);
    xhr.open("POST", url, true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.send(params);
    xhr.onreadystatechange = function () {
        if (xhr.readyState != 4)
            return;
        var tag = document.createElement('p');
        tag.innerHTML = xhr.responseText;
        document.getElementById('msg').appendChild(tag);
    };
}

function delete_sw(url, sw)
{
    var xhr = new XMLHttpRequest();

    var params = 'ext_p=' + encodeURIComponent(sw);
    xhr.open("POST", url, true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.send(params);
    xhr.onreadystatechange = function () {
        if (xhr.readyState != 4)
            return;
        var tag = document.createElement('p');
        tag.innerHTML = xhr.responseText;
        document.getElementById('msg').appendChild(tag);
    };
}

function filter(arg, id, num)
{
    var find = arg.value;
    var elem = document.getElementById(id).children;
    for (var i = 0; i < elem.length; i++)
    {
        if (find == '')
            elem[i].style.display = 'table-row';
        else if (elem[i].children[num].innerHTML.indexOf(find) != -1)
            elem[i].style.display = 'table-row';
        else
            elem[i].style.display = 'none';
    }
}