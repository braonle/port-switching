/**
 * Created by yaroslav on 4/21/16.
 */
function relocate(url)
{
    location.href = url;
}

function confirm_delrt(url, rt)
{
    var res = confirm("Are you sure to delete router " + rt);
    if (res == true) {
        delete_rt(url, rt);
        location.reload();
    }
}

function confirm_delsw(url, sw)
{
    var res = confirm("Are you sure to delete switching rule " + sw);
    if (res == true)
    {
        delete_sw(url, sw);
        location.reload();
    }
}

function delete_rt(url, rt)
{
    var xhr = new XMLHttpRequest();

    var params = 'router=' + encodeURIComponent(rt);
    xhr.open("POST", url, true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.send(params);
}

function delete_sw(url, sw)
{
    var xhr = new XMLHttpRequest();

    var params = 'ext_p=' + encodeURIComponent(sw);
    xhr.open("POST", url, true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.send(params);
}

function filter(arg)
{
    var find = arg.value;
    var elem = arg.parentNode.parentNode.parentNode;
    for (var i = 4; i < elem.childNodes.length; i++)
    {
        var tmp = elem.childNodes[i];
        if (find == '' && tmp.nodeType == 1)
            tmp.style.display = 'table-row';
        else if (tmp.nodeType == 1)
            if (tmp.childNodes[1].innerHTML.indexOf(find) != -1)
                tmp.style.display = 'table-row';
                //tmp.style.color = 'red';
            else
                tmp.style.display = 'none';
                //tmp.style.color = 'black';
    }
}