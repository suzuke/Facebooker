from Facebooker.Facebooker import facebook

if __name__ == '__main__':
    fb_api = facebook.API()
    fb_api.login('fb_account', 'fb_password')
    group_id = 236063346570685
    members_id = fb_api.get_group_member_list(group_id, num=5)
    for member in members_id:
        fb_api.get_user_about(member)