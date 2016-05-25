/**
 * Created by yaroslav on 4/21/16.
 */
function relocate(url)
{
    location.href = url;
}

function confirm_delrt(url, rt)
{
    if (confirm("Are you sure to delete router " + rt))
    {
        delete_rt(url, rt);
        location.reload();
    }
}

function confirm_delsw(url, sw)
{
    if (confirm("Are you sure to delete switching rule " + sw))
    {
        delete_sw(url, sw);
        location.reload();
    }
}

function delete_rt(url, rt)
{
    var xhr = new XMLHttpRequest();

    var params = 'router=' + encodeURIComponent(rt);
    xhr.open("POST", url, false);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.send(params);
}

function delete_sw(url, sw)
{
    var xhr = new XMLHttpRequest();

    var params = 'ext_p=' + encodeURIComponent(sw);
    xhr.open("POST", url, false);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.send(params);

}

function filter(arg, id, num)
{
    var find = arg.value;
    var elem = document.getElementById(id).childNodes[1];
    console.log(elem);
    for (var i = 4; i < elem.childNodes.length; i++)
    {
        var tmp = elem.childNodes[i];
        if (find == '' && tmp.nodeType == 1)
            tmp.style.display = 'table-row';
        else if (tmp.nodeType == 1)
            if (tmp.childNodes[num].innerHTML.indexOf(find) != -1)
                tmp.style.display = 'table-row';
            else
                tmp.style.display = 'none';
    }
}