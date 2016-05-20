/**
 * Created by yaroslav on 4/21/16.
 */
function relocate(url)
{
    location.href = url;
}

function confirm_delrt(url, rt)
{
    res = confirm("Are you sure to delete router " + rt)
    if (res == true) {
        delete_rt(url, rt)
        location.reload()
    }
}

function confirm_delsw(url, sw)
{
    res = confirm("Are you sure to delete switching rule " + sw)
    if (res == true)
    {
        delete_sw(url, sw)
        location.reload()
    }
}

function delete_rt(url, rt)
{
    var xhr = new XMLHttpRequest();

    var params = 'router=' + encodeURIComponent(rt);
    xhr.open("POST", url, true)
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded')
    xhr.send(params);
}

function delete_sw(url, sw)
{
    var xhr = new XMLHttpRequest();

    var params = 'ext_p=' + encodeURIComponent(sw);
    xhr.open("POST", url, true)
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded')
    xhr.send(params);
}