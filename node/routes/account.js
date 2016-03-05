var express = require('express');
var passport = require('passport');
var Account = require('../models/account');
var router = express.Router();

router.use(function(req, res, next) {
  if(req.user) {
    res.locals.user = req.user;
    res.locals.page_settings = {active_page: 'account'};
  }
  return next();
});

router.get('/', function(req, res, next) {
  return res.render('account/index', {
    user: req.user
  });
});

router.route('/register')
.get(function(req, res, next) {
  return res.render('account/register');
})
.post(function(req, res, next) {
  var admin = req.body.username === 'admin' ? true : false;

  return Account.register(new Account({
    username: req.body.username,
    admin: admin
  }), req.body.password, function(err, account) {
    if (err) {
      req.flash('error', 'Account already exists');
      return res.render('account/register', {
        errors: req.flash('error')
      });
    }
    return passport.authenticate('local')(req, res, function() {
      return res.redirect('/account/');
    });
  });
});

router.route('/login')
.get(function(req, res) {
  var data = {
    user: req.user,
    errors: req.flash('error')
  };
  if(req.query.ref) {
    data.ref = req.query.ref;
  }
  return res.render('account/login', data);
})
.post(passport.authenticate('local', {
  failureFlash: true,
  failureRedirect: '/account/login'
}), function(req, res) {
  var defaultRedirect = '/account/';
  return res.redirect(req.query.ref || defaultRedirect);
});

router.get('/logout', function(req, res) {
  req.logout();
  return res.redirect('/account/');
});

router.get('/users-summary', function(req, res) {
  if (req.user && req.user.admin) {
    // query.exec() -> promise
    return Account.find({}).exec().then(function(results) {
      return res.render('account/users-summary', {
        users: results
      });
    });
  } else {
    return res.redirect('/');
  }
});

module.exports = router;
